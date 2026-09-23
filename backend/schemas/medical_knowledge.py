"""
Medical knowledge schemas for the Warrant clinical decision support system.

Every numeric cutoff must trace to a specific, sourced, versioned reference.
Two different sources describing the same clinical claim must be normalized
into a shared schema before they can be compared.
"""

from pydantic import BaseModel
from enum import Enum
from typing import Optional, List, Dict


class ClassOfRecommendation(str, Enum):
    CLASS_I = "I"
    CLASS_IIA = "IIa"
    CLASS_IIB = "IIb"
    CLASS_III = "III"


class LevelOfEvidence(str, Enum):
    A = "A"
    B_R = "B-R"
    B_NR = "B-NR"
    C_LD = "C-LD"
    C_EO = "C-EO"


class EvidenceTier(str, Enum):
    RCT = "RCT"
    COHORT = "COHORT"
    CASE_REPORT = "CASE_REPORT"
    EXPERT_OPINION = "EXPERT_OPINION"
    GUIDELINE = "GUIDELINE"


class SourceCondition(BaseModel):
    """Structured condition from a medical knowledge source."""
    marker: str
    comparison: str  # ">", "<", ">=", "<=", "==", "rise_and_fall"
    reference: str   # e.g. "assay_specific_99th_percentile"
    reference_value: Optional[float] = None
    requires_serial: bool = False
    serial_timeframe_hours: Optional[float] = None


class MedicalKnowledgeSource(BaseModel):
    """A single source of medical knowledge/guidelines."""
    source_id: str
    source_name: str
    version_date: Optional[str] = None
    authority: str
    class_of_recommendation: Optional[ClassOfRecommendation] = None
    level_of_evidence: Optional[LevelOfEvidence] = None
    evidence_tier: Optional[EvidenceTier] = None
    claim: str
    condition: SourceCondition
    population: str
    scope: Optional[str] = None
    provenance: str
    licensing_verified: bool = False
    applicable_context: Optional[str] = None


class StructuredClaim(BaseModel):
    """A normalized medical claim derived from one or more sources."""
    claim_id: str
    claim_type: str
    description: str
    conditions: List[SourceCondition]
    supporting_sources: List[str]
    population: str
    required_evidence: List[str]
    claim_text: str


class AssayReference(BaseModel):
    """Assay reference knowledge — must be sourced before coding.

    Do not hardcode a numeric threshold unless it is explicitly
    tied to one named, sourced assay."""
    assay_name: str
    manufacturer: str
    unit: str
    sex_specific_limits: Dict[str, Optional[float]]
    percentile_99_url: Optional[str] = None
    source_document: str
    version_date: Optional[str] = None
    provenance: str


class SourceAssessment(BaseModel):
    """Assessment of a single source — computed once, reusable across queries.

    Dimensions are kept SEPARATE, never collapsed into one confidence percentage."""
    source_id: str
    reliability: str     # HIGH, MODERATE, LOW, UNKNOWN
    evidence_quality: str
    relevance: str       # DIRECTLY_RELEVANT, PARTIALLY_RELEVANT, NOT_RELEVANT
    applicability: str   # APPLICABLE, PARTIALLY_APPLICABLE, NOT_APPLICABLE, UNKNOWN
    consistency: Optional[str] = None  # set after comparison
    recency_status: str  # CURRENT, AGING, OUTDATED
    population_match: str  # MATCHED, PARTIAL_MATCH, MISMATCH, UNKNOWN
    staleness_years: Optional[float] = None
    notes: Optional[str] = None
