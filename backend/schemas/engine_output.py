"""
Engine output schemas for the Warrant clinical decision support system.

The reasoning engine outputs a structured state object that the LLM
explanation generator is constrained to. The output validator checks
the LLM explanation against this authoritative payload.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict

from backend.schemas.patient_evidence import (
    EvidenceState, ConditionResult, ConflictStatus, CorroborationStatus
)


class ConditionCheck(BaseModel):
    """Result of checking a single condition — always PASS/FAIL/UNKNOWN."""
    condition_name: str
    result: ConditionResult
    reason: str
    evidence_used: Optional[str] = None
    source_reference: Optional[str] = None


class ConflictDetail(BaseModel):
    """Details of a specific conflict between sources."""
    claim: str
    source_a: str
    source_a_position: str
    source_b: str
    source_b_position: str
    resolution_possible: bool = False
    resolution_note: Optional[str] = None


class RetrievalCitation(BaseModel):
    """A retrieved passage used ONLY as citation/grounding.

    SAFETY: Retrieved passages are NEVER interpreted by the LLM into
    executable rules or thresholds. They answer 'can we point to a real
    source consistent with this decision', not 'what is the rule'.
    """
    query: str
    domain: str
    title: str
    snippet: str
    url: Optional[str] = None
    requirement_matched: str
    relevance: str = "UNKNOWN"


class MissingInformation(BaseModel):
    """A specific piece of missing information that may be askable."""
    field: str
    reason_needed: str
    askable: bool = False
    ask_prompt: Optional[str] = None
    criticality: str = "REQUIRED"  # REQUIRED, RECOMMENDED, OPTIONAL


class SourceTraceEntry(BaseModel):
    """A single entry in the provenance trace."""
    source_id: str
    source_name: str
    claim_supported: str
    reliability: str
    recency_status: str
    applicability: str


class ReasoningResult(BaseModel):
    """Complete output of the deterministic reasoning engine."""
    state: EvidenceState
    supported_claims: List[str]
    unsupported_claims: List[str]
    missing_information: List[MissingInformation]
    conflicts: List[ConflictDetail]
    source_trace: List[SourceTraceEntry]
    reasons: List[str]
    condition_checks: List[ConditionCheck]
    conflict_status: ConflictStatus
    corroboration_status: CorroborationStatus
    generic_completeness: ConditionResult
    criteria_specific_completeness: ConditionResult
    retrieval_citations: List[RetrievalCitation] = Field(default_factory=list)


class ActionType(str, Enum):
    """System actions — separate from evidence state (never merged)."""
    RETURN_CONCLUSION = "RETURN_CONCLUSION"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    REPORT_CONFLICT = "REPORT_CONFLICT"
    FLAG_LOW_CONFIDENCE = "FLAG_LOW_CONFIDENCE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    WITHHOLD_CONCLUSION = "WITHHOLD_CONCLUSION"


class StateAction(BaseModel):
    """Maps evidence state to system action."""
    state: EvidenceState
    action: ActionType
    action_description: str
    escalation_required: bool = False


class AnalysisResponse(BaseModel):
    """Complete analysis response sent to the UI."""
    case_id: str
    reasoning_result: ReasoningResult
    action: StateAction
    explanation: str
    explanation_source: str  # "llm" or "template"
    pipeline_trace: Optional[Dict] = None
    timestamp: str
