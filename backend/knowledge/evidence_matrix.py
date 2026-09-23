"""
AMI Evidence Matrix (§4 of the Warrant architecture spec).

For each evidence type, defines: required fields, quality checks,
supportable claims, incompleteness conditions, questionable conditions,
conflict conditions, and what it cannot establish alone.
"""

from typing import Dict, List, Any


class EvidenceMatrix:
    """Codified AMI Evidence Matrix.

    Each evidence type has a complete definition of what it requires,
    what it can support, and what makes it incomplete or questionable.
    """

    _matrix: Dict[str, Dict[str, Any]] = {
        "troponin": {
            "description": "Possible myocardial injury marker",
            "what_it_tells_us": "Possible myocardial injury",
            "required_fields": ["value", "unit", "timestamp", "extraction_confidence"],
            "recommended_fields": ["assay", "serial_values", "extraction_source"],
            "quality_checks": [
                "value must be numeric",
                "unit must be ng/L or pg/mL",
                "assay must be a recognized named assay",
                "serial values must have timestamps",
                "reference limit must match the specific assay",
            ],
            "supportable_claims": [
                "myocardial_injury",
                "elevated_troponin",
                "troponin_rise_fall_pattern",
            ],
            "incompleteness_conditions": [
                "single value without serial data when criterion requires delta",
                "assay unknown (cannot determine reference limit)",
                "no timestamp (cannot assess timing)",
                "unit missing or unrecognized",
            ],
            "questionable_conditions": [
                "extraction confidence < 85%",
                "value is borderline relative to reference",
                "assay reference is from outdated source",
                "sample timing unclear relative to symptom onset",
            ],
            "conflict_conditions": [
                "two sources disagree on the required delta threshold",
                "two sources disagree on the serial timing algorithm",
                "two sources disagree on the 99th percentile reference",
            ],
            "what_it_cannot_establish_alone": "MI by itself",
        },

        "ecg": {
            "description": "Evidence relevant to ischemia",
            "what_it_tells_us": "Evidence relevant to ischemia",
            "required_fields": ["interpretation", "timestamp", "extraction_confidence"],
            "recommended_fields": ["quality", "st_elevation", "st_depression", "comparison_to_prior"],
            "quality_checks": [
                "interpretation must be a recognized category",
                "quality rating present (good/poor/uninterpretable)",
                "comparison to prior noted if available",
            ],
            "supportable_claims": [
                "st_elevation_pattern",
                "st_depression_pattern",
                "ischemic_ecg_changes",
                "new_q_waves",
            ],
            "incompleteness_conditions": [
                "no ECG available",
                "ECG quality uninterpretable",
                "no timestamp",
            ],
            "questionable_conditions": [
                "poor quality recording",
                "extraction confidence < 85%",
                "automated interpretation without physician review",
            ],
            "conflict_conditions": [
                "two readings of same ECG disagree on ST changes",
            ],
            "what_it_cannot_establish_alone": "MI by itself",
        },

        "symptoms": {
            "description": "Clinical context for chest pain evaluation",
            "what_it_tells_us": "Clinical context",
            "required_fields": ["chest_pain", "extraction_confidence"],
            "recommended_fields": ["onset_time", "characteristics", "duration_minutes", "radiation"],
            "quality_checks": [
                "onset time must be a valid datetime",
                "duration must be numeric and in minutes",
                "characteristics should be recognized descriptors",
            ],
            "supportable_claims": [
                "ischemic_symptoms",
                "typical_anginal_chest_pain",
                "atypical_presentation",
            ],
            "incompleteness_conditions": [
                "onset time unknown",
                "symptom characteristics not described",
                "duration unknown",
            ],
            "questionable_conditions": [
                "symptoms described only by patient self-report with no clinician assessment",
                "extraction confidence < 85%",
            ],
            "conflict_conditions": [
                "patient reports conflict with clinical assessment",
            ],
            "what_it_cannot_establish_alone": "MI by itself",
        },

        "imaging": {
            "description": "Structural/functional cardiac abnormality",
            "what_it_tells_us": "Structural/functional abnormality",
            "required_fields": ["modality", "finding", "timestamp", "extraction_confidence"],
            "recommended_fields": ["wall_motion_abnormality", "applicability"],
            "quality_checks": [
                "modality must be recognized (echo, angio, CT, MRI)",
                "finding must be described",
                "applicability to current question noted",
            ],
            "supportable_claims": [
                "new_wall_motion_abnormality",
                "structural_abnormality",
                "coronary_thrombus",
            ],
            "incompleteness_conditions": [
                "no imaging available",
                "imaging modality not applicable to the question",
            ],
            "questionable_conditions": [
                "poor image quality",
                "extraction confidence < 85%",
            ],
            "conflict_conditions": [
                "two imaging studies disagree on wall motion",
            ],
            "what_it_cannot_establish_alone": "whatever that modality can't establish",
        },

        "clinical_history": {
            "description": "Risk context for cardiac assessment",
            "what_it_tells_us": "Risk context",
            "required_fields": ["extraction_confidence"],
            "recommended_fields": ["age", "sex", "diabetes", "smoking", "prior_mi", "prior_pci"],
            "quality_checks": [
                "age must be numeric and reasonable (0-150)",
                "sex must be recognized",
                "risk factors should be boolean or clearly stated",
            ],
            "supportable_claims": [
                "cardiac_risk_factors_present",
                "high_risk_profile",
            ],
            "incompleteness_conditions": [
                "age and sex unknown",
                "risk factor history unavailable",
            ],
            "questionable_conditions": [
                "history from unreliable source",
                "extraction confidence < 85%",
            ],
            "conflict_conditions": [
                "patient-reported history conflicts with medical records",
            ],
            "what_it_cannot_establish_alone": "MI by itself",
        },

        "lab_context": {
            "description": "Supporting laboratory values",
            "what_it_tells_us": "Supporting values",
            "required_fields": ["timestamp", "extraction_confidence"],
            "recommended_fields": ["creatinine", "bnp", "hemoglobin"],
            "quality_checks": [
                "values must be numeric",
                "units must be appropriate for each lab",
                "timing must be relevant to presentation",
            ],
            "supportable_claims": [
                "renal_function_context",
                "cardiac_biomarker_context",
            ],
            "incompleteness_conditions": [
                "relevant comparator labs unavailable",
            ],
            "questionable_conditions": [
                "lab values from different facility without verification",
                "extraction confidence < 85%",
            ],
            "conflict_conditions": [],
            "what_it_cannot_establish_alone": "MI by itself",
        },

        "timing": {
            "description": "Sequencing of clinical events",
            "what_it_tells_us": "Sequencing of events",
            "required_fields": ["extraction_confidence"],
            "recommended_fields": [
                "symptom_onset", "presentation_time",
                "onset_to_presentation_minutes", "serial_sample_spacing_minutes",
            ],
            "quality_checks": [
                "onset and presentation times must be valid datetimes",
                "intervals must be non-negative",
                "serial sample spacing must be appropriate for the algorithm",
            ],
            "supportable_claims": [
                "timing_appropriate_for_serial_algorithm",
                "acute_presentation",
            ],
            "incompleteness_conditions": [
                "symptom onset unknown",
                "serial sampling interval unknown",
            ],
            "questionable_conditions": [
                "onset time approximate or estimated",
                "extraction confidence < 85%",
            ],
            "conflict_conditions": [
                "patient-reported onset conflicts with clinical timeline",
            ],
            "what_it_cannot_establish_alone": "MI by itself",
        },

        "document_quality": {
            "description": "Trustworthiness of the data source itself",
            "what_it_tells_us": "Trustworthiness of the data itself",
            "required_fields": [],
            "recommended_fields": ["document_type", "ocr_confidence", "legibility", "source_file"],
            "quality_checks": [
                "OCR confidence should be above threshold",
                "document type should be recognized",
                "legibility should be assessed",
            ],
            "supportable_claims": [],
            "incompleteness_conditions": [
                "document type unknown",
            ],
            "questionable_conditions": [
                "OCR confidence < 80%",
                "poor legibility",
                "document appears altered or incomplete",
            ],
            "conflict_conditions": [],
            "what_it_cannot_establish_alone": "clinical sufficiency",
        },
    }

    @classmethod
    def get_requirements(cls, evidence_type: str) -> Dict[str, Any]:
        """Get the full requirements definition for an evidence type."""
        if evidence_type not in cls._matrix:
            raise ValueError(f"Unknown evidence type: {evidence_type}")
        return cls._matrix[evidence_type]

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all defined evidence types."""
        return list(cls._matrix.keys())

    @classmethod
    def get_required_fields(cls, evidence_type: str) -> List[str]:
        """Get required fields for an evidence type."""
        return cls._matrix[evidence_type]["required_fields"]

    @classmethod
    def get_supportable_claims(cls, evidence_type: str) -> List[str]:
        """Get claims that this evidence type can support."""
        return cls._matrix[evidence_type]["supportable_claims"]

    @classmethod
    def get_incompleteness_conditions(cls, evidence_type: str) -> List[str]:
        """Get conditions that would make this evidence incomplete."""
        return cls._matrix[evidence_type]["incompleteness_conditions"]
