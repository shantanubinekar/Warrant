"""
Deterministic Reasoning Engine (§3.6) — The heart of the system.

Pure deterministic logic, NO LLM. Uses PASS/FAIL/UNKNOWN for every
individual condition check — UNKNOWN is NOT the same as FAIL.

LLM never decides the evidence state. This engine does.
"""

from typing import List, Optional

from backend.schemas.patient_evidence import (
    PatientCase, EvidenceState, ConditionResult,
    ConflictStatus, CorroborationStatus, ExtractionConfidenceLevel,
)
from backend.schemas.engine_output import (
    ReasoningResult, ConditionCheck, MissingInformation,
    ConflictDetail, SourceTraceEntry,
)
from backend.schemas.medical_knowledge import (
    MedicalKnowledgeSource, StructuredClaim, SourceAssessment, ConditionNode,
)
from backend.knowledge.medical_knowledge_base import MedicalKnowledgeBase
from backend.knowledge.claim_registry import ClaimRegistry
from backend.knowledge.evidence_matrix import EvidenceMatrix
from backend.validators.schema_validator import SchemaValidator
from backend.validators.extraction_confidence import ExtractionConfidenceGate
from backend.pipeline.completeness_checker import CompletenessChecker
from backend.pipeline.source_assessor import SourceAssessor
from backend.pipeline.conflict_detector import ConflictDetector


class ReasoningEngine:
    """Deterministic reasoning engine — the authoritative state producer.

    This engine:
      1. Validates evidence (schema + confidence)
      2. Checks completeness (generic + criteria-specific)
      3. Retrieves and assesses sources
      4. Detects conflicts
      5. Applies deterministic state logic
      6. Produces the authoritative ReasoningResult

    The LLM is NEVER consulted for state determination.
    """

    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.confidence_gate = ExtractionConfidenceGate()
        self.completeness_checker = CompletenessChecker()
        self.source_assessor = SourceAssessor()
        self.conflict_detector = ConflictDetector()
        self.evidence_matrix = EvidenceMatrix()
        self.claim_registry = ClaimRegistry()

    def reason(self, case: PatientCase, knowledge_base: MedicalKnowledgeBase) -> ReasoningResult:
        """Run the full deterministic reasoning pipeline.

        Args:
            case: Validated patient case with all evidence.
            knowledge_base: Curated medical knowledge.

        Returns:
            ReasoningResult with authoritative state and full provenance.
        """
        condition_checks: List[ConditionCheck] = []
        all_missing: List[MissingInformation] = []
        supported_claims: List[str] = []
        unsupported_claims: List[str] = []
        reasons: List[str] = []

        # ── Step 0: Scope and Rule Availability Check ─────────────────
        if case.target_condition:
            available_domains = self.claim_registry.get_available_domains()
            available_claims = self.claim_registry.get_claim_descriptions()
            target_lower = case.target_condition.lower()
            is_domain_match = any(target_lower in d.lower() or d.lower() in target_lower for d in available_domains)
            is_claim_match = self.claim_registry.claim_exists(case.target_condition)

            if not (is_domain_match or is_claim_match):
                covered_domains_str = ", ".join(d.upper() for d in available_domains)
                covered_claims_str = ", ".join(available_claims.keys())
                reasons.append(
                    f"State: RULE_NOT_AVAILABLE — no validated clinical rule entry exists for condition '{case.target_condition}'. "
                    f"Validated domains covered by system: [{covered_domains_str}]. "
                    f"Available claims: [{covered_claims_str}]."
                )
                return ReasoningResult(
                    state=EvidenceState.RULE_NOT_AVAILABLE,
                    supported_claims=[],
                    unsupported_claims=[f"Target condition '{case.target_condition}' is out of scope / not covered"],
                    missing_information=[],
                    conflicts=[],
                    source_trace=[],
                    reasons=reasons,
                    condition_checks=[ConditionCheck(
                        condition_name="rule_availability",
                        result=ConditionResult.FAIL_RESULT,
                        reason=f"No validated knowledge-base entry for '{case.target_condition}'",
                    )],
                    conflict_status=ConflictStatus.NOT_ASSESSABLE,
                    corroboration_status=CorroborationStatus.NOT_ASSESSABLE,
                    generic_completeness=ConditionResult.UNKNOWN,
                    criteria_specific_completeness=ConditionResult.UNKNOWN,
                )

        # ── Step 1: Schema validation ────────────────────────────────
        validation = self.schema_validator.validate_case(case)
        valid_fields = validation["valid_fields"]
        invalid_fields = validation["invalid_fields"]

        for field in invalid_fields:
            condition_checks.append(ConditionCheck(
                condition_name=f"schema_validation_{field}",
                result=ConditionResult.FAIL_RESULT,
                reason=f"Field '{field}' failed schema validation and is treated as absent",
            ))
            reasons.append(f"Schema validation failed for '{field}' — treated as absent")

        # ── Step 2: Extraction confidence gate ───────────────────────
        case = self.confidence_gate.gate_evidence(case)

        # Check for low-confidence critical fields
        has_questionable_evidence = False
        if case.troponin and case.troponin.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
            condition_checks.append(ConditionCheck(
                condition_name="extraction_confidence_troponin",
                result=ConditionResult.UNKNOWN,
                reason="Troponin extraction confidence below 85% — treated as UNKNOWN",
                evidence_used="troponin",
            ))
            has_questionable_evidence = True

        if case.ecg and case.ecg.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
            condition_checks.append(ConditionCheck(
                condition_name="extraction_confidence_ecg",
                result=ConditionResult.UNKNOWN,
                reason="ECG extraction confidence below 85% — treated as UNKNOWN",
                evidence_used="ecg",
            ))
            has_questionable_evidence = True

        # Flag fields at FLAGGED level
        for field_name in ["troponin", "ecg", "symptoms", "imaging"]:
            component = getattr(case, field_name, None)
            if component and hasattr(component, 'confidence_level'):
                if component.confidence_level == ExtractionConfidenceLevel.FLAGGED:
                    condition_checks.append(ConditionCheck(
                        condition_name=f"extraction_confidence_{field_name}",
                        result=ConditionResult.PASS_RESULT,
                        reason=f"{field_name} extraction confidence 85-95% — flagged for verification",
                        evidence_used=field_name,
                    ))

        # ── Step 3: Generic completeness check ───────────────────────
        generic_result, generic_missing = self.completeness_checker.check_generic_completeness(
            case, self.evidence_matrix
        )
        all_missing.extend(generic_missing)

        condition_checks.append(ConditionCheck(
            condition_name="generic_completeness",
            result=generic_result,
            reason=(
                "All present evidence types have required fields"
                if generic_result == ConditionResult.PASS_RESULT
                else "Some evidence fields are structurally incomplete or unusable"
            ),
        ))

        # ── Step 4: Retrieve applicable claims ───────────────────────
        applicable_claims = knowledge_base.get_applicable_claims(case)
        applicable_sources = knowledge_base.get_sources_for_claims(applicable_claims)

        if not applicable_claims:
            condition_checks.append(ConditionCheck(
                condition_name="applicable_criteria",
                result=ConditionResult.UNKNOWN,
                reason="No applicable clinical criteria found for the available evidence",
            ))

        # ── Step 5: Source assessment ────────────────────────────────
        source_assessments = self.source_assessor.assess_all_sources(
            applicable_sources, case
        )

        source_trace = [
            SourceTraceEntry(
                source_id=sa.source_id,
                source_name=knowledge_base.get_source(sa.source_id).source_name
                    if knowledge_base.get_source(sa.source_id) else sa.source_id,
                claim_supported=knowledge_base.get_source(sa.source_id).claim
                    if knowledge_base.get_source(sa.source_id) else "unknown",
                reliability=sa.reliability,
                recency_status=sa.recency_status,
                applicability=sa.applicability,
            )
            for sa in source_assessments
        ]

        # Check for outdated sources
        all_sources_outdated = all(
            sa.recency_status == "OUTDATED"
            for sa in source_assessments
        ) if source_assessments else False

        if all_sources_outdated:
            has_questionable_evidence = True
            reasons.append("All applicable sources are outdated (> 5 years old)")

        # ── Step 6: Criteria-specific completeness ───────────────────
        criteria_result, criteria_missing = self.completeness_checker.check_criteria_completeness(
            case, applicable_claims
        )
        all_missing.extend(criteria_missing)

        condition_checks.append(ConditionCheck(
            condition_name="criteria_specific_completeness",
            result=criteria_result,
            reason=(
                "Evidence satisfies criteria-specific requirements"
                if criteria_result == ConditionResult.PASS_RESULT
                else "Evidence does not satisfy all criteria-specific requirements"
            ),
        ))

        # ── Step 7: Conflict detection ───────────────────────────────
        conflict_status, corroboration_status, conflicts = self.conflict_detector.detect_conflicts(
            applicable_sources, source_assessments
        )

        if conflict_status == ConflictStatus.CONFLICT:
            condition_checks.append(ConditionCheck(
                condition_name="source_conflict_check",
                result=ConditionResult.FAIL_RESULT,
                reason=f"{len(conflicts)} material conflict(s) detected between applicable sources",
            ))
        else:
            condition_checks.append(ConditionCheck(
                condition_name="source_conflict_check",
                result=ConditionResult.PASS_RESULT if conflict_status == ConflictStatus.NO_CONFLICT
                    else ConditionResult.UNKNOWN,
                reason=(
                    "No conflicts between applicable sources"
                    if conflict_status == ConflictStatus.NO_CONFLICT
                    else "Conflict assessment not possible (fewer than 2 applicable sources)"
                ),
            ))

        # ── Step 8: Clinical criteria evaluation ─────────────────────
        criteria_met, passed_claims, failed_claims = self._evaluate_clinical_criteria(
            case, applicable_claims, knowledge_base, condition_checks,
            supported_claims, unsupported_claims, reasons
        )

        # ── Step 9: Deterministic state logic ────────────────────────
        state = self._determine_state(
            generic_result=generic_result,
            criteria_result=criteria_result,
            criteria_met=criteria_met,
            conflict_status=conflict_status,
            has_questionable_evidence=has_questionable_evidence,
            all_missing=all_missing,
            condition_checks=condition_checks,
            reasons=reasons,
            passed_claims=passed_claims,
            failed_claims=failed_claims,
        )

        # Determine askable missing information
        askable_missing = [m for m in all_missing if m.askable]

        return ReasoningResult(
            state=state,
            supported_claims=supported_claims,
            unsupported_claims=unsupported_claims,
            missing_information=all_missing,
            conflicts=conflicts,
            source_trace=source_trace,
            reasons=reasons,
            condition_checks=condition_checks,
            conflict_status=conflict_status,
            corroboration_status=corroboration_status,
            generic_completeness=generic_result,
            criteria_specific_completeness=criteria_result,
        )

    def _evaluate_clinical_criteria(
        self,
        case: PatientCase,
        applicable_claims: List[StructuredClaim],
        knowledge_base: MedicalKnowledgeBase,
        condition_checks: List[ConditionCheck],
        supported_claims: List[str],
        unsupported_claims: List[str],
        reasons: List[str],
    ) -> tuple[ConditionResult, List[StructuredClaim], List[StructuredClaim]]:
        """Evaluate clinical criteria against patient evidence.

        Returns (result, passed_claims, failed_claims).
        """
        if not applicable_claims:
            return ConditionResult.UNKNOWN, [], []

        any_pass = False
        any_unknown = False
        passed_claims: List[StructuredClaim] = []
        failed_claims: List[StructuredClaim] = []

        for claim in applicable_claims:
            result = self.evaluate_claim(
                claim, case, knowledge_base, condition_checks, reasons
            )
            if result == ConditionResult.PASS_RESULT:
                supported_claims.append(claim.claim_text)
                passed_claims.append(claim)
                any_pass = True
            elif result == ConditionResult.UNKNOWN:
                any_unknown = True
                failed_claims.append(claim)
                # Don't add to unsupported_claims list — UNKNOWN ≠ FAIL
            else:
                unsupported_claims.append(claim.claim_text)
                failed_claims.append(claim)

        if any_pass:
            return ConditionResult.PASS_RESULT, passed_claims, failed_claims
        if any_unknown:
            return ConditionResult.UNKNOWN, passed_claims, failed_claims
        return ConditionResult.FAIL_RESULT, passed_claims, failed_claims

    def evaluate_claim(
        self,
        claim: StructuredClaim,
        case: PatientCase,
        knowledge_base: MedicalKnowledgeBase,
        condition_checks: List[ConditionCheck],
        reasons: List[str],
    ) -> ConditionResult:
        """Generic evaluation of a structured claim via its condition tree.

        Interprets AND/OR/NOT condition trees recursively.
        Leaves are domain-agnostic condition checks.
        No hardcoded disease-specific methods.
        """
        condition_tree = claim.condition_tree
        if condition_tree is None:
            registry_claim = self.claim_registry.get_claim(claim.claim_id)
            if registry_claim:
                condition_tree = registry_claim.condition_tree

        if condition_tree is None:
            return ConditionResult.UNKNOWN

        return self._evaluate_condition_node(
            condition_tree, case, claim, knowledge_base, condition_checks, reasons
        )

    def _evaluate_condition_node(
        self,
        node: ConditionNode,
        case: PatientCase,
        claim: StructuredClaim,
        knowledge_base: MedicalKnowledgeBase,
        condition_checks: List[ConditionCheck],
        reasons: List[str],
    ) -> ConditionResult:
        """Evaluate a condition tree node recursively."""
        node_type = (node.type or "").upper()

        if node_type == "AND":
            any_unknown = False
            for child in (node.children or []):
                res = self._evaluate_condition_node(
                    child, case, claim, knowledge_base, condition_checks, reasons
                )
                if res == ConditionResult.FAIL_RESULT:
                    return ConditionResult.FAIL_RESULT
                if res == ConditionResult.UNKNOWN:
                    any_unknown = True
            return ConditionResult.UNKNOWN if any_unknown else ConditionResult.PASS_RESULT

        elif node_type == "OR":
            any_unknown = False
            for child in (node.children or []):
                res = self._evaluate_condition_node(
                    child, case, claim, knowledge_base, condition_checks, reasons
                )
                if res == ConditionResult.PASS_RESULT:
                    return ConditionResult.PASS_RESULT
                if res == ConditionResult.UNKNOWN:
                    any_unknown = True
            return ConditionResult.UNKNOWN if any_unknown else ConditionResult.FAIL_RESULT

        elif node_type == "NOT":
            if not node.children:
                return ConditionResult.UNKNOWN
            res = self._evaluate_condition_node(
                node.children[0], case, claim, knowledge_base, condition_checks, reasons
            )
            if res == ConditionResult.PASS_RESULT:
                return ConditionResult.FAIL_RESULT
            if res == ConditionResult.FAIL_RESULT:
                return ConditionResult.PASS_RESULT
            return ConditionResult.UNKNOWN

        elif node_type == "CONDITION":
            return self._evaluate_leaf_condition(
                node, case, claim, knowledge_base, condition_checks, reasons
            )

        return ConditionResult.UNKNOWN

    def _evaluate_leaf_condition(
        self,
        node: ConditionNode,
        case: PatientCase,
        claim: StructuredClaim,
        knowledge_base: MedicalKnowledgeBase,
        condition_checks: List[ConditionCheck],
        reasons: List[str],
    ) -> ConditionResult:
        """Evaluate an individual leaf condition check."""
        check = (node.check or "").upper()

        # ── Leaf Check: TROPONIN_ABOVE_99TH ──────────────────────────────
        if check == "TROPONIN_ABOVE_99TH":
            if not case.troponin or case.troponin.value is None:
                return ConditionResult.UNKNOWN
            if case.troponin.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                return ConditionResult.UNKNOWN

            assay_ref = None
            if case.troponin.assay:
                assay_ref = knowledge_base.get_assay_reference(case.troponin.assay)
                if not assay_ref:
                    assay_ref = self.claim_registry.get_assay_reference_fuzzy(case.troponin.assay)
                if not assay_ref:
                    condition_checks.append(ConditionCheck(
                        condition_name=f"assay_match_{claim.claim_id}",
                        result=ConditionResult.UNKNOWN,
                        reason=f"Assay '{case.troponin.assay}' not found in reference database",
                        evidence_used="troponin",
                    ))
                    reasons.append(f"Troponin assay '{case.troponin.assay}' not in reference database — comparison result is UNKNOWN")
                    return ConditionResult.UNKNOWN
            else:
                condition_checks.append(ConditionCheck(
                    condition_name=f"assay_known_{claim.claim_id}",
                    result=ConditionResult.UNKNOWN,
                    reason="Troponin assay unknown — cannot determine reference limit",
                    evidence_used="troponin",
                ))
                reasons.append("Troponin assay is unknown — reference comparison is UNKNOWN, not a guess")
                return ConditionResult.UNKNOWN

            # Sex-specific 99th percentile URL
            sex = case.clinical_history.sex.lower() if (case.clinical_history and case.clinical_history.sex) else None
            if sex in ("female", "f"):
                url_value = assay_ref.sex_specific_limits.get("female")
            elif sex in ("male", "m"):
                url_value = assay_ref.sex_specific_limits.get("male")
            else:
                url_value = assay_ref.sex_specific_limits.get("male")

            if url_value is None:
                condition_checks.append(ConditionCheck(
                    condition_name=f"reference_limit_{claim.claim_id}",
                    result=ConditionResult.UNKNOWN,
                    reason="No reference limit available for this assay/sex combination",
                    evidence_used="troponin",
                ))
                return ConditionResult.UNKNOWN

            troponin_elevated = case.troponin.value > url_value
            condition_checks.append(ConditionCheck(
                condition_name=f"troponin_vs_99th_{claim.claim_id}",
                result=ConditionResult.PASS_RESULT if troponin_elevated else ConditionResult.FAIL_RESULT,
                reason=(
                    f"Troponin {case.troponin.value} {case.troponin.unit} is "
                    f"{'above' if troponin_elevated else 'at or below'} 99th percentile URL "
                    f"of {url_value} {assay_ref.unit} ({assay_ref.assay_name})"
                ),
                evidence_used="troponin",
                source_reference=assay_ref.source_document,
            ))

            if troponin_elevated:
                reasons.append(f"Troponin elevated above 99th percentile for {assay_ref.assay_name}")
                return ConditionResult.PASS_RESULT
            return ConditionResult.FAIL_RESULT

        # ── Leaf Check: SERIAL_RISE_FALL ─────────────────────────────────
        elif check == "SERIAL_RISE_FALL":
            if not case.troponin or case.troponin.value is None:
                return ConditionResult.UNKNOWN

            if case.troponin.serial_values and len(case.troponin.serial_values) >= 1:
                min_change = (node.params or {}).get("min_relative_change", 0.20)
                has_rise_fall = self._has_relative_change(
                    case.troponin.value, case.troponin.serial_values, min_change
                )
                condition_checks.append(ConditionCheck(
                    condition_name=f"rise_fall_pattern_{claim.claim_id}",
                    result=ConditionResult.PASS_RESULT if has_rise_fall else ConditionResult.FAIL_RESULT,
                    reason=(
                        "Rise and/or fall pattern detected in serial troponin values"
                        if has_rise_fall
                        else "No significant rise/fall pattern in serial troponin values"
                    ),
                    evidence_used="troponin_serial",
                ))
                return ConditionResult.PASS_RESULT if has_rise_fall else ConditionResult.FAIL_RESULT
            else:
                condition_checks.append(ConditionCheck(
                    condition_name=f"serial_data_{claim.claim_id}",
                    result=ConditionResult.UNKNOWN,
                    reason="Serial troponin data not available — cannot assess rise/fall pattern",
                    evidence_used="troponin",
                ))
                return ConditionResult.UNKNOWN

        # ── Leaf Check: PRESENT ──────────────────────────────────────────
        elif check == "PRESENT":
            evidence_type = (node.evidence_type or "").lower()
            field_name = node.field

            component = getattr(case, evidence_type, None)
            if not component:
                return ConditionResult.UNKNOWN
            if getattr(component, "confidence_level", None) == ExtractionConfidenceLevel.UNKNOWN:
                return ConditionResult.UNKNOWN

            val = getattr(component, field_name, None) if field_name else True
            if val is True:
                condition_checks.append(ConditionCheck(
                    condition_name=f"{evidence_type}_{field_name}_{claim.claim_id}",
                    result=ConditionResult.PASS_RESULT,
                    reason=f"{evidence_type} {field_name} is present/positive",
                    evidence_used=evidence_type,
                ))
                return ConditionResult.PASS_RESULT
            elif val is False:
                condition_checks.append(ConditionCheck(
                    condition_name=f"{evidence_type}_{field_name}_{claim.claim_id}",
                    result=ConditionResult.FAIL_RESULT,
                    reason=f"{evidence_type} {field_name} is absent/negative",
                    evidence_used=evidence_type,
                ))
                return ConditionResult.FAIL_RESULT
            elif val is not None:
                condition_checks.append(ConditionCheck(
                    condition_name=f"{evidence_type}_{field_name}_{claim.claim_id}",
                    result=ConditionResult.PASS_RESULT,
                    reason=f"{evidence_type} {field_name} is present: {val}",
                    evidence_used=evidence_type,
                ))
                return ConditionResult.PASS_RESULT
            else:
                return ConditionResult.UNKNOWN

        # ── Leaf Check: NOT_PRESENT ──────────────────────────────────────
        elif check == "NOT_PRESENT":
            evidence_type = (node.evidence_type or "").lower()
            field_name = node.field
            component = getattr(case, evidence_type, None)
            if not component:
                return ConditionResult.PASS_RESULT
            val = getattr(component, field_name, None) if field_name else False
            if val is False or val is None:
                return ConditionResult.PASS_RESULT
            return ConditionResult.FAIL_RESULT

        return ConditionResult.UNKNOWN

    def _has_relative_change(self, baseline_value: float, serial_values: List[dict], min_change: float = 0.20) -> bool:
        """Generic relative change calculator for serial values."""
        if not serial_values:
            return False
        values = [baseline_value] + [sv.get("value", 0) for sv in serial_values if sv.get("value") is not None]
        if len(values) < 2:
            return False
        max_val = max(values)
        min_val = min(values)
        if max_val == 0:
            return False
        relative_change = (max_val - min_val) / max_val
        return relative_change >= min_change

    def _determine_state(
        self,
        generic_result: ConditionResult,
        criteria_result: ConditionResult,
        criteria_met: ConditionResult,
        conflict_status: ConflictStatus,
        has_questionable_evidence: bool,
        all_missing: List[MissingInformation],
        condition_checks: List[ConditionCheck],
        reasons: List[str],
        passed_claims: Optional[List[StructuredClaim]] = None,
        failed_claims: Optional[List[StructuredClaim]] = None,
    ) -> EvidenceState:
        """Apply deterministic state logic (§3.6) with rich unknown & weaker claim states.

        Priority ordering:
        1. CONFLICTING (if sources materially disagree)
        2. QUESTIONABLE (if critical evidence has unacceptable quality)
        3. INCOMPLETE / ADDITIONAL_INFORMATION_REQUIRED (if critical info missing)
        4. WEAKER_CLAIM_ONLY (if evidence supports only a weaker claim)
        5. SUFFICIENT (if all conditions pass)
        6. NO_RELIABLE_CONCLUSION (fallback)
        """
        # 1. Conflict check
        if conflict_status == ConflictStatus.CONFLICT:
            reasons.append("State: CONFLICTING — applicable sources materially disagree")
            return EvidenceState.CONFLICTING

        # 2. Questionable evidence check
        if has_questionable_evidence:
            reasons.append("State: QUESTIONABLE — critical evidence has unacceptable quality/provenance")
            return EvidenceState.QUESTIONABLE

        # 3. Missing critical information & Weaker Claim Check
        weaker_claim_eligible = False
        if passed_claims:
            passed_ranks = [c.strength_rank for c in passed_claims]
            failed_ranks = [c.strength_rank for c in (failed_claims or [])]
            if max(passed_ranks) == 1 and any(r > 1 for r in failed_ranks):
                weaker_claim_eligible = True

        required_missing = [m for m in all_missing if m.criticality == "REQUIRED"]
        # If weaker claim is satisfied and missing info is only for the stronger claim
        if weaker_claim_eligible:
            weaker_missing = [m for m in required_missing if "troponin" in m.field.lower() or "serial" in m.field.lower()]
            if not weaker_missing:
                reasons.append(
                    "State: WEAKER_CLAIM_ONLY — evidence supports a weaker claim (e.g. myocardial injury) "
                    "but cannot establish the primary diagnosis (acute myocardial infarction)"
                )
                return EvidenceState.WEAKER_CLAIM_ONLY

        askable_missing = [m for m in required_missing if m.askable]
        if required_missing:
            if askable_missing:
                reasons.append(
                    f"State: INCOMPLETE + ADDITIONAL_INFORMATION_REQUIRED — "
                    f"{len(askable_missing)} askable item(s) could resolve uncertainty"
                )
                return EvidenceState.ADDITIONAL_INFORMATION_REQUIRED
            else:
                reasons.append("State: INCOMPLETE — required evidence is missing")
                return EvidenceState.INCOMPLETE

        # 4. Weaker claim check (when no missing info)
        if weaker_claim_eligible:
            reasons.append(
                "State: WEAKER_CLAIM_ONLY — evidence supports a weaker claim (e.g. myocardial injury) "
                "but cannot establish the primary diagnosis (acute myocardial infarction)"
            )
            return EvidenceState.WEAKER_CLAIM_ONLY

        # 5. Check if all conditions pass → SUFFICIENT
        if (generic_result == ConditionResult.PASS_RESULT
                and criteria_result == ConditionResult.PASS_RESULT
                and criteria_met == ConditionResult.PASS_RESULT
                and conflict_status != ConflictStatus.CONFLICT):
            reasons.append("State: SUFFICIENT — all evidence conditions satisfied")
            return EvidenceState.SUFFICIENT

        # 6. If criteria result is UNKNOWN (not FAIL)
        if criteria_met == ConditionResult.UNKNOWN:
            if askable_missing:
                reasons.append("State: ADDITIONAL_INFORMATION_REQUIRED — specific items would help")
                return EvidenceState.ADDITIONAL_INFORMATION_REQUIRED
            else:
                reasons.append(
                    "State: NO_RELIABLE_CONCLUSION — evidence cannot establish the claim "
                    "and no further recoverable action exists"
                )
                return EvidenceState.NO_RELIABLE_CONCLUSION

        # 7. Fallback
        reasons.append(
            "State: NO_RELIABLE_CONCLUSION — the available evidence cannot establish "
            "the requested claim with no further recoverable action"
        )
        return EvidenceState.NO_RELIABLE_CONCLUSION
