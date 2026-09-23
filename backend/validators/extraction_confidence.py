"""
Extraction Confidence Gate (§3.2).

Per-field confidence gating with engineering starting points:
  >= 95% → ACCEPTED (eligible for PASS/FAIL evaluation)
  85-95% → FLAGGED (flag for verification/review)
  < 85%  → UNKNOWN (engine must treat as missing)

These are engineering starting points, NOT clinically validated cutoffs.
Low confidence ≠ false value — it means "we don't know."
"""

from backend.schemas.patient_evidence import (
    PatientCase, ExtractionConfidenceLevel,
)

# Thresholds — engineering starting points, not clinically validated
ACCEPT_THRESHOLD = 0.95
FLAG_THRESHOLD = 0.85


class ExtractionConfidenceGate:
    """Per-field confidence gating.

    Note: These thresholds are engineering starting points, not clinically
    validated cutoffs. Critical fields (troponin, ECG read) may warrant
    stricter bands than routine text fields.
    """

    @staticmethod
    def gate_field(field_name: str, confidence: float) -> ExtractionConfidenceLevel:
        """Classify a single field's extraction confidence.

        Args:
            field_name: Name of the evidence field (for logging).
            confidence: Extraction confidence score 0.0-1.0.

        Returns:
            ExtractionConfidenceLevel classification.
        """
        if confidence >= ACCEPT_THRESHOLD:
            return ExtractionConfidenceLevel.ACCEPTED
        elif confidence >= FLAG_THRESHOLD:
            return ExtractionConfidenceLevel.FLAGGED
        else:
            return ExtractionConfidenceLevel.UNKNOWN

    def gate_evidence(self, case: PatientCase) -> PatientCase:
        """Apply confidence gate to all evidence components in a case.

        Returns a new PatientCase with confidence_level set on each component.
        Components with confidence < 85% get level=UNKNOWN and the engine
        must treat them as missing.
        """
        # Process each evidence component
        if case.troponin:
            case.troponin.confidence_level = self.gate_field(
                "troponin", case.troponin.extraction_confidence
            )
            if case.troponin.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.troponin.schema_valid = False

        if case.ecg:
            case.ecg.confidence_level = self.gate_field(
                "ecg", case.ecg.extraction_confidence
            )
            if case.ecg.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.ecg.schema_valid = False

        if case.symptoms:
            case.symptoms.confidence_level = self.gate_field(
                "symptoms", case.symptoms.extraction_confidence
            )
            if case.symptoms.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.symptoms.schema_valid = False

        if case.imaging:
            case.imaging.confidence_level = self.gate_field(
                "imaging", case.imaging.extraction_confidence
            )
            if case.imaging.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.imaging.schema_valid = False

        if case.clinical_history:
            case.clinical_history.confidence_level = self.gate_field(
                "clinical_history", case.clinical_history.extraction_confidence
            )
            if case.clinical_history.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.clinical_history.schema_valid = False

        if case.lab_context:
            case.lab_context.confidence_level = self.gate_field(
                "lab_context", case.lab_context.extraction_confidence
            )
            if case.lab_context.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.lab_context.schema_valid = False

        if case.timing:
            case.timing.confidence_level = self.gate_field(
                "timing", case.timing.extraction_confidence
            )
            if case.timing.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                case.timing.schema_valid = False

        return case
