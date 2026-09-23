"""
Patient evidence schemas for the Warrant clinical decision support system.

All patient evidence fields carry extraction confidence, provenance, and
verification status. The deterministic engine never trusts a value without
checking these metadata fields.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Any
from datetime import datetime


class EvidenceState(str, Enum):
    """Six mutually exclusive evidence states from the Warrant architecture."""
    SUFFICIENT = "SUFFICIENT"
    INCOMPLETE = "INCOMPLETE"
    CONFLICTING = "CONFLICTING"
    QUESTIONABLE = "QUESTIONABLE"
    ADDITIONAL_INFORMATION_REQUIRED = "ADDITIONAL_INFORMATION_REQUIRED"
    NO_RELIABLE_CONCLUSION = "NO_RELIABLE_CONCLUSION"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"


class ConditionResult(str, Enum):
    """PASS/FAIL/UNKNOWN for every individual condition check.
    UNKNOWN is NOT the same as FAIL — it means 'we don't know'."""
    PASS_RESULT = "PASS"
    FAIL_RESULT = "FAIL"
    UNKNOWN = "UNKNOWN"


class ConflictStatus(str, Enum):
    CONFLICT = "CONFLICT"
    NO_CONFLICT = "NO_CONFLICT"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


class CorroborationStatus(str, Enum):
    CORROBORATED = "CORROBORATED"
    NOT_CORROBORATED = "NOT_CORROBORATED"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"
    LIMITED_CORROBORATION = "LIMITED_CORROBORATION"


class ExtractionConfidenceLevel(str, Enum):
    """Engineering starting points — not clinically validated cutoffs."""
    ACCEPTED = "ACCEPTED"       # >= 95%
    FLAGGED = "FLAGGED"         # 85-95%
    UNKNOWN = "UNKNOWN"         # < 85%


# ─── Individual evidence models ────────────────────────────────────────

class TroponinEvidence(BaseModel):
    """Troponin measurement with assay traceability."""
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    assay: Optional[str] = None
    serial_values: Optional[List[dict]] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class ECGEvidence(BaseModel):
    """ECG findings relevant to ischemia assessment."""
    interpretation: Optional[str] = None
    st_elevation: Optional[bool] = None
    st_depression: Optional[bool] = None
    q_waves: Optional[bool] = None
    timestamp: Optional[datetime] = None
    quality: Optional[str] = None
    comparison_to_prior: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class SymptomsEvidence(BaseModel):
    """Clinical symptoms relevant to ACS assessment."""
    chest_pain: Optional[bool] = None
    onset_time: Optional[datetime] = None
    characteristics: Optional[str] = None
    duration_minutes: Optional[float] = None
    radiation: Optional[str] = None
    associated_symptoms: Optional[List[str]] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class ImagingEvidence(BaseModel):
    """Cardiac imaging findings."""
    modality: Optional[str] = None
    finding: Optional[str] = None
    wall_motion_abnormality: Optional[bool] = None
    timestamp: Optional[datetime] = None
    applicability: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class ClinicalHistory(BaseModel):
    """Patient clinical history and risk factors."""
    age: Optional[int] = None
    sex: Optional[str] = None
    diabetes: Optional[bool] = None
    hypertension: Optional[bool] = None
    smoking: Optional[bool] = None
    prior_mi: Optional[bool] = None
    prior_pci: Optional[bool] = None
    prior_cabg: Optional[bool] = None
    family_history_cad: Optional[bool] = None
    renal_disease: Optional[bool] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class LabContext(BaseModel):
    """Supporting laboratory values."""
    creatinine: Optional[float] = None
    bnp: Optional[float] = None
    hemoglobin: Optional[float] = None
    platelets: Optional[float] = None
    inr: Optional[float] = None
    relevant_comparators: Optional[dict] = None
    timestamp: Optional[datetime] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class TimingEvidence(BaseModel):
    """Temporal sequencing of clinical events."""
    symptom_onset: Optional[datetime] = None
    presentation_time: Optional[datetime] = None
    onset_to_presentation_minutes: Optional[float] = None
    serial_sample_spacing_minutes: Optional[float] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None


class DocumentQuality(BaseModel):
    """Quality metadata about the source document itself."""
    document_type: Optional[str] = None
    ocr_confidence: Optional[float] = None
    legibility: Optional[str] = None
    source_file: Optional[str] = None


class EvidenceField(BaseModel):
    """Generic evidence field with full provenance — used for raw extraction."""
    field: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    provenance: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    schema_valid: bool = False
    confidence_level: Optional[ExtractionConfidenceLevel] = None
    notes: Optional[str] = None


class PatientCase(BaseModel):
    """Complete patient case with all evidence types."""
    case_id: str
    case_description: Optional[str] = None
    troponin: Optional[TroponinEvidence] = None
    ecg: Optional[ECGEvidence] = None
    symptoms: Optional[SymptomsEvidence] = None
    imaging: Optional[ImagingEvidence] = None
    clinical_history: Optional[ClinicalHistory] = None
    lab_context: Optional[LabContext] = None
    timing: Optional[TimingEvidence] = None
    document_quality: Optional[DocumentQuality] = None
    raw_evidence_fields: Optional[List[EvidenceField]] = None
