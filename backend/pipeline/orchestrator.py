"""
Pipeline Orchestrator — ties all stages into a single callable pipeline.

Implements the full flowchart from §1 of the architecture spec:
  Input → Schema Validation → Confidence Gate → Generic Completeness →
  Retrieve Claims → Source Assessment → Criteria-Specific Completeness →
  Conflict Detection → Reasoning Engine → State→Action → LLM Explanation →
  Output Validation → Response
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from backend.schemas.patient_evidence import (
    PatientCase, EvidenceState, ConditionResult,
    ConflictStatus, CorroborationStatus,
)
from backend.schemas.engine_output import (
    AnalysisResponse, ReasoningResult, StateAction, ConditionCheck,
)
from backend.engine.reasoning_engine import ReasoningEngine
from backend.engine.state_action_mapper import StateActionMapper
from backend.validators.output_validator import OutputValidator
from backend.knowledge.medical_knowledge_base import MedicalKnowledgeBase
from backend.retrieval.retrieval_manager import RetrievalManager

logger = logging.getLogger(__name__)

# Maximum LLM explanation retries before template fallback
MAX_EXPLANATION_RETRIES = 2


class PipelineOrchestrator:
    """Orchestrates the full Warrant reasoning pipeline.

    Coordinates all pipeline stages from validated patient evidence
    through to a final AnalysisResponse. The LLM is only used for
    explanation generation — never for state determination.
    """

    def __init__(self, llm_client=None, enable_retrieval: Optional[bool] = None):
        """
        Args:
            llm_client: Optional LLM client for explanation generation.
                        If None, uses template fallback for all explanations.
            enable_retrieval: Whether to run live web search retrieval. Defaults
                              to ENABLE_WEB_RETRIEVAL env var (default: True).
        """
        import os
        if enable_retrieval is None:
            enable_retrieval = os.environ.get("ENABLE_WEB_RETRIEVAL", "true").lower() in ("1", "true", "yes")
        self.enable_retrieval = enable_retrieval
        self.reasoning_engine = ReasoningEngine()
        self.state_action_mapper = StateActionMapper()
        self.output_validator = OutputValidator()
        self.knowledge_base = MedicalKnowledgeBase()
        self.retrieval_manager = RetrievalManager()
        self.llm_client = llm_client

    def run_pipeline(self, case: PatientCase) -> AnalysisResponse:
        """Run the full deterministic pipeline on a patient case.

        Args:
            case: Validated PatientCase with all evidence.

        Returns:
            AnalysisResponse with state, explanation, and full provenance.
        """
        # ── Scope & Rule Availability Check (BEFORE retrieval or reasoning) ──
        if case.target_condition:
            registry = self.reasoning_engine.claim_registry
            available_domains = registry.get_available_domains()
            available_claims = registry.get_claim_descriptions()
            target_lower = case.target_condition.lower()
            is_domain_match = any(target_lower in d.lower() or d.lower() in target_lower for d in available_domains)
            is_claim_match = registry.claim_exists(case.target_condition)

            if not (is_domain_match or is_claim_match):
                logger.info(f"Target condition '{case.target_condition}' is not in knowledge base — triggering RULE_NOT_AVAILABLE")
                covered_domains_str = ", ".join(d.upper() for d in available_domains)
                
                reasoning_result = ReasoningResult(
                    state=EvidenceState.RULE_NOT_AVAILABLE,
                    supported_claims=[],
                    unsupported_claims=[f"Target condition '{case.target_condition}' is not covered by validated knowledge base entries"],
                    missing_information=[],
                    conflicts=[],
                    source_trace=[],
                    reasons=[
                        f"State: RULE_NOT_AVAILABLE — no validated clinical rule or guideline entry exists for condition '{case.target_condition}'.",
                        f"Validated knowledge domains currently supported: [{covered_domains_str}].",
                    ],
                    condition_checks=[ConditionCheck(
                        condition_name="rule_availability",
                        result=ConditionResult.FAIL_RESULT,
                        reason=f"No validated knowledge-base entry for '{case.target_condition}'",
                    )],
                    conflict_status=ConflictStatus.NOT_ASSESSABLE,
                    corroboration_status=CorroborationStatus.NOT_ASSESSABLE,
                    generic_completeness=ConditionResult.UNKNOWN,
                    criteria_specific_completeness=ConditionResult.UNKNOWN,
                    retrieval_citations=[],
                )
                action = self.state_action_mapper.map_state_to_action(reasoning_result.state, reasoning_result)
                explanation = (
                    f"## Evidence Assessment: RULE_NOT_AVAILABLE\n\n"
                    f"No validated clinical rule or guideline entry exists for condition '{case.target_condition}'.\n"
                    f"The system operates exclusively on validated clinical knowledge and withholds conclusions "
                    f"for out-of-scope conditions.\n\n"
                    f"### Covered Domains & Rules\n"
                    f"The system currently supports the following validated medical domains:\n"
                    f"  • {covered_domains_str}\n\n"
                    f"Covered clinical claims:\n"
                    f"  • " + "\n  • ".join(f"{cid}: {desc}" for cid, desc in available_claims.items())
                )
                return AnalysisResponse(
                    case_id=case.case_id,
                    reasoning_result=reasoning_result,
                    action=action,
                    explanation=explanation,
                    explanation_source="template",
                    pipeline_trace={"pipeline_stages": ["rule_availability_check"]},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        # ── Step: Live Web Retrieval for Grounding / Citations ───────────
        # CRITICAL: Retrieved passages are CITATIONS ONLY — NEVER rules.
        citations = []
        if self.enable_retrieval:
            try:
                self.retrieval_manager.reset()
                applicable_claims = self.knowledge_base.get_applicable_claims(case)
                for claim in applicable_claims:
                    claim_citations = self.retrieval_manager.retrieve_for_claim(claim)
                    citations.extend(claim_citations)
            except Exception as e:
                logger.warning(f"Retrieval error: {e}")

        # ── Steps 1–9: Deterministic reasoning (inside ReasoningEngine) ──
        reasoning_result = self.reasoning_engine.reason(case, self.knowledge_base)
        reasoning_result.retrieval_citations = citations
        logger.info(f"Reasoning result state: {reasoning_result.state.value}")

        # ── Step: State → Action mapping ─────────────────────────────────
        action = self.state_action_mapper.map_state_to_action(
            reasoning_result.state, reasoning_result
        )
        logger.info(f"Action: {action.action.value} — {action.action_description}")

        # ── Steps: LLM explanation + output validation ───────────────────
        explanation, explanation_source = self._generate_validated_explanation(
            reasoning_result, action
        )

        # ── Build pipeline trace ─────────────────────────────────────────
        pipeline_trace = self._build_pipeline_trace(case, reasoning_result, action)

        # ── Assemble final response ──────────────────────────────────────
        response = AnalysisResponse(
            case_id=case.case_id,
            reasoning_result=reasoning_result,
            action=action,
            explanation=explanation,
            explanation_source=explanation_source,
            pipeline_trace=pipeline_trace,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"Pipeline complete for case {case.case_id}: {reasoning_result.state.value}")
        return response

    def _generate_validated_explanation(
        self,
        reasoning_result: ReasoningResult,
        action: StateAction,
    ) -> tuple[str, str]:
        """Generate LLM explanation with output validation, falling back to template.

        Returns:
            (explanation_text, source) where source is "llm" or "template"
        """
        # If no LLM client, go straight to template
        if self.llm_client is None:
            logger.info("No LLM client — using template fallback")
            return (
                self.output_validator.generate_template_fallback(reasoning_result),
                "template",
            )

        # Try LLM explanation with validation
        for attempt in range(1, MAX_EXPLANATION_RETRIES + 1):
            try:
                explanation = self.llm_client.generate_explanation(
                    reasoning_result, action
                )

                # Validate the LLM output
                passed, violations = self.output_validator.validate_explanation(
                    explanation, reasoning_result
                )

                if passed:
                    logger.info(f"LLM explanation passed validation on attempt {attempt}")
                    return (explanation, "llm")
                else:
                    logger.warning(
                        f"LLM explanation failed validation (attempt {attempt}): "
                        f"{violations}"
                    )
            except Exception as e:
                logger.error(f"LLM explanation generation failed (attempt {attempt}): {e}")

        # All retries exhausted — use template fallback
        logger.warning("LLM explanation failed after all retries — using template fallback")
        return (
            self.output_validator.generate_template_fallback(reasoning_result),
            "template",
        )

    def _build_pipeline_trace(
        self,
        case: PatientCase,
        reasoning_result: ReasoningResult,
        action: StateAction,
    ) -> dict:
        """Build a trace of the full pipeline execution for provenance."""
        return {
            "case_id": case.case_id,
            "pipeline_stages": [
                {
                    "stage": "schema_validation",
                    "status": "completed",
                },
                {
                    "stage": "extraction_confidence_gate",
                    "status": "completed",
                },
                {
                    "stage": "generic_completeness_check",
                    "result": reasoning_result.generic_completeness.value,
                },
                {
                    "stage": "criteria_specific_completeness",
                    "result": reasoning_result.criteria_specific_completeness.value,
                },
                {
                    "stage": "source_assessment",
                    "sources_assessed": len(reasoning_result.source_trace),
                },
                {
                    "stage": "conflict_detection",
                    "conflict_status": reasoning_result.conflict_status.value,
                    "conflicts_found": len(reasoning_result.conflicts),
                },
                {
                    "stage": "deterministic_reasoning",
                    "state": reasoning_result.state.value,
                    "condition_checks": len(reasoning_result.condition_checks),
                },
                {
                    "stage": "state_action_mapping",
                    "action": action.action.value,
                    "escalation_required": action.escalation_required,
                },
            ],
            "total_condition_checks": len(reasoning_result.condition_checks),
            "total_sources": len(reasoning_result.source_trace),
            "total_missing_info": len(reasoning_result.missing_information),
            "total_conflicts": len(reasoning_result.conflicts),
        }
