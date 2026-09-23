"""
Schema Validator (§3.1) — Format/structure check ONLY, never clinical judgment.

Catches: wrong data type, missing required keys, invalid/unrecognized units,
malformed timestamps, invalid codes. A field failing here is treated as
absent downstream, not as its raw (possibly garbage) value.
"""

from typing import Dict, List, Tuple
from backend.schemas.patient_evidence import PatientCase, TroponinEvidence, ECGEvidence


VALID_TROPONIN_UNITS = {"ng/l", "ng/L", "pg/mL", "pg/ml", "ug/L", "ug/l"}
VALID_ECG_QUALITIES = {"good", "poor", "uninterpretable", "adequate", "fair"}
VALID_IMAGING_MODALITIES = {"echo", "echocardiogram", "angiography", "ct", "mri", "cta", "pet"}
VALID_LEGIBILITY = {"good", "partial", "poor"}


class SchemaValidator:
    """Deterministic format/structure validator — no clinical judgment."""

    def validate_case(self, case: PatientCase) -> Dict[str, List]:
        """Validate all evidence components in a patient case.

        Returns:
            dict with keys: valid_fields, invalid_fields, validation_errors
        """
        valid_fields: List[str] = []
        invalid_fields: List[str] = []
        validation_errors: List[str] = []

        # Validate troponin
        if case.troponin:
            is_valid, errors = self.validate_troponin(case.troponin)
            if is_valid:
                valid_fields.append("troponin")
            else:
                invalid_fields.append("troponin")
                validation_errors.extend(errors)

        # Validate ECG
        if case.ecg:
            is_valid, errors = self.validate_ecg(case.ecg)
            if is_valid:
                valid_fields.append("ecg")
            else:
                invalid_fields.append("ecg")
                validation_errors.extend(errors)

        # Validate symptoms
        if case.symptoms:
            is_valid, errors = self._validate_component(
                "symptoms", case.symptoms,
                required_type_checks={"chest_pain": bool}
            )
            if is_valid:
                valid_fields.append("symptoms")
            else:
                invalid_fields.append("symptoms")
                validation_errors.extend(errors)

        # Validate imaging
        if case.imaging:
            errors = []
            valid = True
            if case.imaging.modality and case.imaging.modality.lower() not in VALID_IMAGING_MODALITIES:
                errors.append(f"imaging: unrecognized modality '{case.imaging.modality}'")
                valid = False
            if valid:
                valid_fields.append("imaging")
            else:
                invalid_fields.append("imaging")
                validation_errors.extend(errors)

        # Validate clinical history
        if case.clinical_history:
            errors = []
            valid = True
            if case.clinical_history.age is not None:
                if not isinstance(case.clinical_history.age, int) or case.clinical_history.age < 0 or case.clinical_history.age > 150:
                    errors.append("clinical_history: age must be integer 0-150")
                    valid = False
            if case.clinical_history.sex is not None:
                if case.clinical_history.sex.lower() not in {"male", "female", "m", "f", "other"}:
                    errors.append(f"clinical_history: unrecognized sex '{case.clinical_history.sex}'")
                    valid = False
            if valid:
                valid_fields.append("clinical_history")
            else:
                invalid_fields.append("clinical_history")
                validation_errors.extend(errors)

        # Validate lab context
        if case.lab_context:
            errors = []
            valid = True
            for lab_field in ["creatinine", "bnp", "hemoglobin", "platelets", "inr"]:
                val = getattr(case.lab_context, lab_field, None)
                if val is not None and not isinstance(val, (int, float)):
                    errors.append(f"lab_context: {lab_field} must be numeric, got {type(val).__name__}")
                    valid = False
            if valid:
                valid_fields.append("lab_context")
            else:
                invalid_fields.append("lab_context")
                validation_errors.extend(errors)

        # Validate timing
        if case.timing:
            valid_fields.append("timing")

        # Validate document quality
        if case.document_quality:
            errors = []
            valid = True
            if case.document_quality.legibility and case.document_quality.legibility.lower() not in VALID_LEGIBILITY:
                errors.append(f"document_quality: unrecognized legibility '{case.document_quality.legibility}'")
                valid = False
            if valid:
                valid_fields.append("document_quality")
            else:
                invalid_fields.append("document_quality")
                validation_errors.extend(errors)

        return {
            "valid_fields": valid_fields,
            "invalid_fields": invalid_fields,
            "validation_errors": validation_errors,
        }

    def validate_troponin(self, troponin: TroponinEvidence) -> Tuple[bool, List[str]]:
        """Validate troponin evidence — structure only."""
        errors = []

        if troponin.value is not None and not isinstance(troponin.value, (int, float)):
            errors.append(f"troponin: value must be numeric, got {type(troponin.value).__name__}")

        if troponin.unit and troponin.unit not in VALID_TROPONIN_UNITS:
            errors.append(f"troponin: unrecognized unit '{troponin.unit}'")

        if troponin.serial_values:
            for i, sv in enumerate(troponin.serial_values):
                if "value" not in sv:
                    errors.append(f"troponin: serial_values[{i}] missing 'value'")
                elif not isinstance(sv["value"], (int, float)):
                    errors.append(f"troponin: serial_values[{i}].value must be numeric")
                if "timestamp" not in sv:
                    errors.append(f"troponin: serial_values[{i}] missing 'timestamp'")

        return (len(errors) == 0, errors)

    def validate_ecg(self, ecg: ECGEvidence) -> Tuple[bool, List[str]]:
        """Validate ECG evidence — structure only."""
        errors = []

        if ecg.quality and ecg.quality.lower() not in VALID_ECG_QUALITIES:
            errors.append(f"ecg: unrecognized quality '{ecg.quality}'")

        return (len(errors) == 0, errors)

    def _validate_component(self, name: str, component, required_type_checks: dict = None) -> Tuple[bool, List[str]]:
        """Generic validation for a component with type checks."""
        errors = []
        if required_type_checks:
            for field_name, expected_type in required_type_checks.items():
                val = getattr(component, field_name, None)
                if val is not None and not isinstance(val, expected_type):
                    errors.append(f"{name}: {field_name} expected {expected_type.__name__}, got {type(val).__name__}")
        return (len(errors) == 0, errors)
