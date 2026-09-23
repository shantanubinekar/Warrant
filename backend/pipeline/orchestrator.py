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

from backend.schemas.patient_evidence import PatientCase
from backend.schemas.engine_output import AnalysisResponse, ReasoningResult, StateAction
from backend.engine.reasoning_engine import ReasoningEngine
from backend.engine.state_action_mapper import StateActionMapper
from backend.validators.output_validator import OutputValidator
from backend.knowledge.medical_knowledge_base import MedicalKnowledgeBase

logger = logging.getLogger(__name__)

# Maximum LLM explanation retries before template fallback
MAX_EXPLANATION_RETRIES = 2


class PipelineOrchestrator:
    """Orchestrates the full Warrant reasoning pipeline.

    Coordinates all pipeline stages from validated patient evidence
    through to a final AnalysisResponse. The LLM is only used for
    explanation generation — never for state determination.
    """

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: Optional LLM client for explanation generation.
                        If None, uses template fallback for all explanations.
        """
        self.reasoning_engine = ReasoningEngine()
        self.state_action_mapper = StateActionMapper()
        self.output_validator = OutputValidator()
        self.knowledge_base = MedicalKnowledgeBase()
        self.llm_client = llm_client

    def run_pipeline(self, case: PatientCase) -> AnalysisResponse:
        """Run the full deterministic pipeline on a patient case.

        Args:
            case: Validated PatientCase with all evidence.

        Returns:
            AnalysisResponse with state, explanation, and full provenance.
        """
        logger.info(f"Running pipeline for case: {case.case_id}")

        # ── Steps 1–9: Deterministic reasoning (inside ReasoningEngine) ──
        reasoning_result = self.reasoning_engine.reason(case, self.knowledge_base)
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
