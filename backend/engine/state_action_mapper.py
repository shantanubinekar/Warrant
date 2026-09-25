"""
State → Action Mapper (§3.7).

State (a fact about evidence) and action (what the system does about it)
are SEPARATE fields — never merge them.
"""

from backend.schemas.patient_evidence import EvidenceState
from backend.schemas.engine_output import ReasoningResult, StateAction, ActionType


class StateActionMapper:
    """Maps evidence states to system actions.

    State and action are separate concepts:
      - State: what the evidence tells us
      - Action: what the system does about it
    """

    # Default mapping per §3.7
    _mapping = {
        EvidenceState.SUFFICIENT: (
            ActionType.RETURN_CONCLUSION,
            "Evidence is sufficient. Returning conclusion with full provenance trace.",
            False,
        ),
        EvidenceState.INCOMPLETE: (
            ActionType.REQUEST_INFORMATION,
            "Evidence is incomplete. Requesting specific additional information.",
            False,
        ),
        EvidenceState.ADDITIONAL_INFORMATION_REQUIRED: (
            ActionType.REQUEST_INFORMATION,
            "Specific additional information is required and can be requested.",
            False,
        ),
        EvidenceState.CONFLICTING: (
            ActionType.REPORT_CONFLICT,
            "Sources conflict on material criteria. Reporting the conflict explicitly without picking a side.",
            False,
        ),
        EvidenceState.QUESTIONABLE: (
            ActionType.FLAG_LOW_CONFIDENCE,
            "Evidence quality is questionable. Returning conclusion flagged as low-confidence.",
            False,
        ),
        EvidenceState.NO_RELIABLE_CONCLUSION: (
            ActionType.ESCALATE_TO_HUMAN,
            "No reliable conclusion can be reached. Escalating to human clinician for review.",
            True,
        ),
        EvidenceState.WEAKER_CLAIM_ONLY: (
            ActionType.RETURN_CONCLUSION,
            "Evidence supports only a weaker claim. Primary diagnosis cannot be established.",
            False,
        ),
        EvidenceState.RULE_NOT_AVAILABLE: (
            ActionType.WITHHOLD_CONCLUSION,
            "No validated clinical rule or guideline entry is available for this condition in the knowledge base.",
            False,
        ),
    }

    def map_state_to_action(
        self,
        state: EvidenceState,
        reasoning_result: ReasoningResult,
    ) -> StateAction:
        """Map an evidence state to the appropriate system action.

        Args:
            state: The authoritative evidence state from the reasoning engine.
            reasoning_result: Full reasoning result for context.

        Returns:
            StateAction with the mapped action and description.
        """
        action_type, description, escalation = self._mapping[state]

        # Customize description based on reasoning result details
        if state == EvidenceState.ADDITIONAL_INFORMATION_REQUIRED:
            askable = [m for m in reasoning_result.missing_information if m.askable]
            if askable:
                items = ", ".join(m.field for m in askable)
                description = f"Additional information required: {items}. Specific requests have been generated."

        if state == EvidenceState.CONFLICTING and reasoning_result.conflicts:
            n = len(reasoning_result.conflicts)
            description = (
                f"{n} material conflict(s) detected between applicable sources. "
                f"Reporting all conflicts explicitly — the system does not pick a side."
            )

        return StateAction(
            state=state,
            action=action_type,
            action_description=description,
            escalation_required=escalation,
        )
