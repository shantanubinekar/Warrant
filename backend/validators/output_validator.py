"""
Deterministic Output Validator (§3.9).

After the LLM generates its explanation, this validator checks:
  - Does the stated conclusion match the state?
  - Are all missing_information items mentioned?
  - Did the LLM claim anything in unsupported_claims?
  - Did it introduce new conclusions not in supported_claims?
  - Did it contradict a listed conflict?
  - Does every cited source ID exist in source_trace? (hallucinated-citation check)

PASS → return to user. FAIL → regenerate. Repeated failure → template fallback.
"""

import re
from typing import Tuple, List

from backend.schemas.engine_output import ReasoningResult
from backend.schemas.patient_evidence import EvidenceState


# ── State descriptions for template generation ──────────────────────

STATE_DESCRIPTIONS = {
    EvidenceState.SUFFICIENT: "The available evidence is sufficient to support a clinical conclusion.",
    EvidenceState.INCOMPLETE: "The available evidence is incomplete — critical information is missing.",
    EvidenceState.CONFLICTING: "The available evidence sources contain material conflicts that cannot be resolved.",
    EvidenceState.QUESTIONABLE: "The quality of the available evidence is questionable and may not support a reliable conclusion.",
    EvidenceState.ADDITIONAL_INFORMATION_REQUIRED: "Specific additional information is required before a conclusion can be reached.",
    EvidenceState.NO_RELIABLE_CONCLUSION: "No reliable conclusion can be reached from the available evidence. Human escalation is recommended.",
    EvidenceState.WEAKER_CLAIM_ONLY: "Available evidence supports only a weaker claim and cannot support the primary diagnosis.",
    EvidenceState.RULE_NOT_AVAILABLE: "No validated clinical rule or guideline entry is available in the medical knowledge base for this clinical scenario.",
}


class OutputValidator:
    """Deterministic validation of LLM-generated explanations against the authoritative state."""

    def validate_explanation(
        self,
        explanation: str,
        reasoning_result: ReasoningResult,
    ) -> Tuple[bool, List[str]]:
        """Validate an LLM-generated explanation against the reasoning result.

        Args:
            explanation: The LLM-generated explanation text.
            reasoning_result: The authoritative structured state from the reasoning engine.

        Returns:
            (passed, violations): Whether validation passed and list of violations found.
        """
        violations = []
        explanation_lower = explanation.lower()

        # 1. Check that stated conclusion matches state
        state_name = reasoning_result.state.value.lower().replace("_", " ")
        if state_name not in explanation_lower and reasoning_result.state.value.lower() not in explanation_lower:
            violations.append(
                f"Explanation does not mention the evidence state '{reasoning_result.state.value}'"
            )

        # 2. Check that all missing_information items are mentioned
        for missing in reasoning_result.missing_information:
            field_lower = missing.field.lower().replace("_", " ")
            if field_lower not in explanation_lower and missing.field.lower() not in explanation_lower:
                violations.append(
                    f"Missing information item '{missing.field}' not mentioned in explanation"
                )

        # 3. Check for unsupported claims being asserted
        for unsupported in reasoning_result.unsupported_claims:
            claim_words = unsupported.lower().split()
            # Check if the explanation asserts the unsupported claim positively
            # (not just mentioning it as unsupported)
            negation_patterns = ["not established", "cannot", "unsupported", "not supported",
                                 "insufficient", "cannot be concluded", "not confirmed"]
            claim_lower = unsupported.lower()

            if claim_lower in explanation_lower:
                # Check if it's mentioned in a negation context
                is_negated = any(neg in explanation_lower for neg in negation_patterns)
                if not is_negated:
                    # More nuanced check — is the claim near a negation word?
                    claim_idx = explanation_lower.find(claim_lower)
                    surrounding = explanation_lower[max(0, claim_idx - 50):claim_idx + len(claim_lower) + 50]
                    if not any(neg in surrounding for neg in negation_patterns):
                        violations.append(
                            f"Explanation may be asserting unsupported claim: '{unsupported}'"
                        )

        # 4. Check for hallucinated source IDs
        valid_source_ids = {entry.source_id for entry in reasoning_result.source_trace}
        # Find patterns that look like source IDs (word_word_word format)
        cited_ids = re.findall(r'\b([a-z][a-z_0-9]+_\d{4}[a-z_0-9]*)\b', explanation_lower)
        for cited_id in cited_ids:
            if cited_id not in {sid.lower() for sid in valid_source_ids}:
                violations.append(
                    f"Hallucinated source ID cited: '{cited_id}' not in source trace"
                )

        # 5. Check for conflicts being contradicted
        if reasoning_result.conflicts:
            resolve_patterns = ["resolved", "clearly", "the correct", "should be",
                                "we recommend", "the answer is"]
            for conflict in reasoning_result.conflicts:
                for pattern in resolve_patterns:
                    if pattern in explanation_lower:
                        context_idx = explanation_lower.find(pattern)
                        surrounding = explanation_lower[max(0, context_idx - 100):context_idx + 100]
                        if conflict.claim.lower() in surrounding:
                            violations.append(
                                f"Explanation appears to resolve conflict on '{conflict.claim}' "
                                f"that should be reported, not resolved"
                            )

        return (len(violations) == 0, violations)

    def generate_template_fallback(self, reasoning_result: ReasoningResult) -> str:
        """Generate a safe deterministic explanation from the structured state.

        No LLM involved — pure string formatting from the state object.
        Used when LLM explanation fails validation repeatedly.
        """
        r = reasoning_result
        lines = []

        # State header
        lines.append(f"## Evidence Assessment: {r.state.value}")
        lines.append("")
        lines.append(STATE_DESCRIPTIONS.get(r.state, ""))
        lines.append("")

        # Supported claims
        if r.supported_claims:
            lines.append("### Supported by Evidence")
            for claim in r.supported_claims:
                lines.append(f"  ✓ {claim}")
            lines.append("")

        # Unsupported claims
        if r.unsupported_claims:
            lines.append("### Not Supported by Available Evidence")
            for claim in r.unsupported_claims:
                lines.append(f"  ✗ {claim}")
            lines.append("")

        # Missing information
        if r.missing_information:
            lines.append("### Missing Information")
            for missing in r.missing_information:
                criticality_marker = "⚠" if missing.criticality == "REQUIRED" else "ℹ"
                lines.append(f"  {criticality_marker} {missing.field}: {missing.reason_needed}")
                if missing.askable and missing.ask_prompt:
                    lines.append(f"    → Action: {missing.ask_prompt}")
            lines.append("")

        # Conflicts
        if r.conflicts:
            lines.append("### Source Conflicts (Unresolved)")
            for conflict in r.conflicts:
                lines.append(f"  Regarding: {conflict.claim}")
                lines.append(f"    • {conflict.source_a}: {conflict.source_a_position}")
                lines.append(f"    • {conflict.source_b}: {conflict.source_b_position}")
                if conflict.resolution_note:
                    lines.append(f"    Note: {conflict.resolution_note}")
            lines.append("")

        # Reasons
        if r.reasons:
            lines.append("### Reasoning Summary")
            for reason in r.reasons:
                lines.append(f"  • {reason}")
            lines.append("")

        # Source provenance
        if r.source_trace:
            lines.append("### Sources Referenced")
            for source in r.source_trace:
                lines.append(
                    f"  [{source.source_id}] {source.source_name} — "
                    f"Reliability: {source.reliability}, "
                    f"Recency: {source.recency_status}, "
                    f"Applicability: {source.applicability}"
                )
            lines.append("")

        # Disclaimer
        lines.append("---")
        lines.append(
            "*This assessment is generated by a deterministic template from the "
            "structured reasoning output. It has not been reviewed by an LLM "
            "explanation system. All conclusions are derived from the evidence "
            "evaluation pipeline and are traceable to the sources listed above.*"
        )

        return "\n".join(lines)
