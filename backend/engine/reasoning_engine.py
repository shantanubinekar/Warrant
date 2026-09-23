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
    MedicalKnowledgeSource, StructuredClaim, SourceAssessment,
)
from backend.knowledge.medical_knowledge_base import MedicalKnowledgeBase
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
        criteria_met = self._evaluate_clinical_criteria(
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
    ) -> ConditionResult:
        """Evaluate clinical criteria against patient evidence.

        Returns PASS if criteria are met, FAIL if explicitly not met,
        UNKNOWN if cannot determine.
        """
        if not applicable_claims:
            return ConditionResult.UNKNOWN

        any_pass = False
        any_unknown = False

        for claim in applicable_claims:
            result = self._evaluate_single_claim(
                case, claim, knowledge_base, condition_checks, reasons
            )
            if result == ConditionResult.PASS_RESULT:
                supported_claims.append(claim.claim_text)
                any_pass = True
            elif result == ConditionResult.UNKNOWN:
                any_unknown = True
                # Don't add to unsupported — UNKNOWN ≠ FAIL
            else:
                unsupported_claims.append(claim.claim_text)

        if any_pass:
            return ConditionResult.PASS_RESULT
        if any_unknown:
            return ConditionResult.UNKNOWN
        return ConditionResult.FAIL_RESULT

    def _evaluate_single_claim(
        self,
        case: PatientCase,
        claim: StructuredClaim,
        knowledge_base: MedicalKnowledgeBase,
        condition_checks: List[ConditionCheck],
        reasons: List[str],
    ) -> ConditionResult:
        """Evaluate a single clinical claim against patient evidence."""

        if claim.claim_type == "myocardial_injury":
            return self._check_myocardial_injury(case, claim, knowledge_base, condition_checks, reasons)
        elif claim.claim_type == "ami_diagnosis":
            return self._check_ami(case, claim, knowledge_base, condition_checks, reasons)
        elif claim.claim_type == "stemi_criteria":
            return self._check_stemi(case, claim, condition_checks, reasons)
        elif claim.claim_type == "nstemi_criteria":
            return self._check_nstemi(case, claim, knowledge_base, condition_checks, reasons)
        elif claim.claim_type == "rapid_rule_in":
            return self._check_myocardial_injury(case, claim, knowledge_base, condition_checks, reasons)
        else:
            return ConditionResult.UNKNOWN

    def _check_myocardial_injury(
        self, case, claim, knowledge_base, condition_checks, reasons
    ) -> ConditionResult:
        """Check troponin against assay reference for myocardial injury."""
        if not case.troponin or case.troponin.value is None:
            return ConditionResult.UNKNOWN

        if case.troponin.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
            return ConditionResult.UNKNOWN

        # Get assay reference
        assay_ref = None
        if case.troponin.assay:
            assay_ref = knowledge_base.get_assay_reference(case.troponin.assay)
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
            # Assay unknown → reference comparison is UNKNOWN, never a guess
            condition_checks.append(ConditionCheck(
                condition_name=f"assay_known_{claim.claim_id}",
                result=ConditionResult.UNKNOWN,
                reason="Troponin assay unknown — cannot determine reference limit",
                evidence_used="troponin",
            ))
            reasons.append("Troponin assay is unknown — reference comparison is UNKNOWN, not a guess")
            return ConditionResult.UNKNOWN

        # Compare against 99th percentile URL
        sex = case.clinical_history.sex.lower() if (case.clinical_history and case.clinical_history.sex) else None
        if sex in ("female", "f"):
            url_value = assay_ref.sex_specific_limits.get("female")
        elif sex in ("male", "m"):
            url_value = assay_ref.sex_specific_limits.get("male")
        else:
            # Use higher (male) limit as conservative default when sex unknown
            url_value = assay_ref.sex_specific_limits.get("male")

        if url_value is None:
            condition_checks.append(ConditionCheck(
                condition_name=f"reference_limit_{claim.claim_id}",
                result=ConditionResult.UNKNOWN,
                reason="No reference limit available for this assay/sex combination",
                evidence_used="troponin",
            ))
            return ConditionResult.UNKNOWN

        # Check if troponin is above 99th percentile
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

        if not troponin_elevated:
            return ConditionResult.FAIL_RESULT

        # Check for rise and/or fall pattern (requires serial)
        for condition in claim.conditions:
            if condition.requires_serial:
                if case.troponin.serial_values and len(case.troponin.serial_values) >= 1:
                    has_rise_fall = self._check_rise_fall_pattern(
                        case.troponin.value, case.troponin.serial_values
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
                    if not has_rise_fall:
                        return ConditionResult.FAIL_RESULT
                else:
                    # No serial data — cannot assess rise/fall
                    condition_checks.append(ConditionCheck(
                        condition_name=f"serial_data_{claim.claim_id}",
                        result=ConditionResult.UNKNOWN,
                        reason="Serial troponin data not available — cannot assess rise/fall pattern",
                        evidence_used="troponin",
                    ))
                    return ConditionResult.UNKNOWN

        reasons.append(f"Troponin elevated above 99th percentile for {assay_ref.assay_name}")
        return ConditionResult.PASS_RESULT

    def _check_ami(self, case, claim, knowledge_base, condition_checks, reasons) -> ConditionResult:
        """Check AMI Type 1: myocardial injury + acute ischemia evidence."""
        # First check myocardial injury
        injury_result = self._check_myocardial_injury(case, claim, knowledge_base, condition_checks, reasons)
        if injury_result != ConditionResult.PASS_RESULT:
            return injury_result

        # Then check for clinical ischemia evidence
        has_ischemia = False
        ischemia_evidence = []

        if case.symptoms and case.symptoms.chest_pain:
            has_ischemia = True
            ischemia_evidence.append("ischemic symptoms (chest pain)")

        if case.ecg:
            if case.ecg.st_elevation:
                has_ischemia = True
                ischemia_evidence.append("ST elevation on ECG")
            if case.ecg.st_depression:
                has_ischemia = True
                ischemia_evidence.append("ST depression on ECG")
            if case.ecg.q_waves:
                has_ischemia = True
                ischemia_evidence.append("new Q waves on ECG")

        if case.imaging and case.imaging.wall_motion_abnormality:
            has_ischemia = True
            ischemia_evidence.append("new wall motion abnormality on imaging")

        condition_checks.append(ConditionCheck(
            condition_name=f"clinical_ischemia_{claim.claim_id}",
            result=ConditionResult.PASS_RESULT if has_ischemia else ConditionResult.FAIL_RESULT,
            reason=(
                f"Clinical ischemia evidence present: {', '.join(ischemia_evidence)}"
                if has_ischemia
                else "No clinical ischemia evidence found (symptoms, ECG changes, or imaging)"
            ),
        ))

        if has_ischemia:
            reasons.append(f"Clinical ischemia evidence: {', '.join(ischemia_evidence)}")
            return ConditionResult.PASS_RESULT
        return ConditionResult.FAIL_RESULT

    def _check_stemi(self, case, claim, condition_checks, reasons) -> ConditionResult:
        """Check STEMI criteria: ST elevation in 2+ contiguous leads."""
        if not case.ecg:
            return ConditionResult.UNKNOWN

        if case.ecg.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
            return ConditionResult.UNKNOWN

        if case.ecg.st_elevation is True:
            condition_checks.append(ConditionCheck(
                condition_name=f"stemi_ecg_{claim.claim_id}",
                result=ConditionResult.PASS_RESULT,
                reason="ST elevation pattern identified on ECG",
                evidence_used="ecg",
            ))
            reasons.append("STEMI pattern: ST elevation on ECG")
            return ConditionResult.PASS_RESULT
        elif case.ecg.st_elevation is False:
            condition_checks.append(ConditionCheck(
                condition_name=f"stemi_ecg_{claim.claim_id}",
                result=ConditionResult.FAIL_RESULT,
                reason="No ST elevation on ECG",
                evidence_used="ecg",
            ))
            return ConditionResult.FAIL_RESULT
        else:
            return ConditionResult.UNKNOWN

    def _check_nstemi(self, case, claim, knowledge_base, condition_checks, reasons) -> ConditionResult:
        """Check NSTEMI: myocardial injury + ischemia without ST elevation."""
        injury_result = self._check_myocardial_injury(case, claim, knowledge_base, condition_checks, reasons)
        if injury_result != ConditionResult.PASS_RESULT:
            return injury_result

        # Must NOT have ST elevation
        if case.ecg and case.ecg.st_elevation is True:
            condition_checks.append(ConditionCheck(
                condition_name=f"no_st_elevation_{claim.claim_id}",
                result=ConditionResult.FAIL_RESULT,
                reason="ST elevation present — this is STEMI, not NSTEMI",
                evidence_used="ecg",
            ))
            return ConditionResult.FAIL_RESULT

        # Must have ischemia evidence
        has_ischemia = (
            (case.symptoms and case.symptoms.chest_pain) or
            (case.ecg and case.ecg.st_depression) or
            (case.imaging and case.imaging.wall_motion_abnormality)
        )

        if has_ischemia:
            reasons.append("NSTEMI pattern: elevated troponin with ischemia, no ST elevation")
            return ConditionResult.PASS_RESULT
        return ConditionResult.UNKNOWN

    def _check_rise_fall_pattern(self, baseline_value: float, serial_values: List[dict]) -> bool:
        """Check for significant rise and/or fall pattern in serial troponin."""
        if not serial_values:
            return False

        values = [baseline_value] + [sv.get("value", 0) for sv in serial_values if sv.get("value") is not None]
        if len(values) < 2:
            return False

        # Check for rise: any subsequent value > 20% higher than baseline
        # or fall: any subsequent value > 20% lower than peak
        max_val = max(values)
        min_val = min(values)

        if max_val == 0:
            return False

        # Significant change threshold: 20% relative change
        relative_change = (max_val - min_val) / max_val
        return relative_change >= 0.20

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
    ) -> EvidenceState:
        """Apply the deterministic state logic (§3.6).

        Priority ordering for state determination:
        1. CONFLICTING (if sources materially disagree)
        2. QUESTIONABLE (if critical evidence has unacceptable quality)
        3. INCOMPLETE / ADDITIONAL_INFORMATION_REQUIRED (if critical info missing)
        4. SUFFICIENT (if all conditions pass)
        5. NO_RELIABLE_CONCLUSION (fallback)
        """

        # Check for conflicts first
        if conflict_status == ConflictStatus.CONFLICT:
            reasons.append("State: CONFLICTING — applicable sources materially disagree")
            return EvidenceState.CONFLICTING

        # Check for questionable evidence
        if has_questionable_evidence:
            reasons.append("State: QUESTIONABLE — critical evidence has unacceptable quality/provenance")
            return EvidenceState.QUESTIONABLE

        # Check for missing critical information
        required_missing = [m for m in all_missing if m.criticality == "REQUIRED"]
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

        # Check if all conditions pass → SUFFICIENT
        if (generic_result == ConditionResult.PASS_RESULT
                and criteria_result == ConditionResult.PASS_RESULT
                and criteria_met == ConditionResult.PASS_RESULT
                and conflict_status != ConflictStatus.CONFLICT):
            reasons.append("State: SUFFICIENT — all evidence conditions satisfied")
            return EvidenceState.SUFFICIENT

        # If criteria result is UNKNOWN (not FAIL) and we have some evidence
        if criteria_met == ConditionResult.UNKNOWN:
            # Check if there's anything askable
            if askable_missing:
                reasons.append("State: ADDITIONAL_INFORMATION_REQUIRED — specific items would help")
                return EvidenceState.ADDITIONAL_INFORMATION_REQUIRED
            else:
                reasons.append(
                    "State: NO_RELIABLE_CONCLUSION — evidence cannot establish the claim "
                    "and no further recoverable action exists"
                )
                return EvidenceState.NO_RELIABLE_CONCLUSION

        # Fallback
        reasons.append(
            "State: NO_RELIABLE_CONCLUSION — the available evidence cannot establish "
            "the requested claim with no further recoverable action"
        )
        return EvidenceState.NO_RELIABLE_CONCLUSION
