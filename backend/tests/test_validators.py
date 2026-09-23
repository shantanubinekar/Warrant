"""
Tests for Validators: SchemaValidator, ExtractionConfidenceGate, OutputValidator.
"""

import pytest
from datetime import datetime

from backend.validators.schema_validator import SchemaValidator
from backend.validators.extraction_confidence import ExtractionConfidenceGate
from backend.validators.output_validator import OutputValidator

from backend.schemas.patient_evidence import (
    PatientCase, TroponinEvidence, ECGEvidence, SymptomsEvidence,
    ClinicalHistory, VerificationStatus, ExtractionConfidenceLevel,
    EvidenceState, ConditionResult, ConflictStatus, CorroborationStatus,
)
from backend.schemas.engine_output import (
    ReasoningResult, ConditionCheck, MissingInformation,
    SourceTraceEntry,
)


# ── Schema Validator Tests ───────────────────────────────────────────


class TestSchemaValidator:
    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_valid_troponin(self, validator):
        case = PatientCase(
            case_id="test",
            troponin=TroponinEvidence(
                value=50.0, unit="ng/L",
                timestamp=datetime(2026, 1, 1),
                extraction_confidence=0.98,
                schema_valid=True,
            ),
        )
        result = validator.validate_case(case)
        assert "troponin" in result["valid_fields"]
        assert "troponin" not in result["invalid_fields"]

    def test_invalid_troponin_unit(self, validator):
        case = PatientCase(
            case_id="test",
            troponin=TroponinEvidence(
                value=50.0, unit="invalid_unit",
                timestamp=datetime(2026, 1, 1),
                extraction_confidence=0.98,
                schema_valid=True,
            ),
        )
        result = validator.validate_case(case)
        assert "troponin" in result["invalid_fields"]

    def test_valid_ecg(self, validator):
        case = PatientCase(
            case_id="test",
            ecg=ECGEvidence(
                interpretation="normal",
                quality="good",
                timestamp=datetime(2026, 1, 1),
                extraction_confidence=0.97,
                schema_valid=True,
            ),
        )
        result = validator.validate_case(case)
        assert "ecg" in result["valid_fields"]

    def test_invalid_ecg_quality(self, validator):
        case = PatientCase(
            case_id="test",
            ecg=ECGEvidence(
                interpretation="normal",
                quality="terrible",  # Not in valid set
                timestamp=datetime(2026, 1, 1),
                extraction_confidence=0.97,
                schema_valid=True,
            ),
        )
        result = validator.validate_case(case)
        assert "ecg" in result["invalid_fields"]

    def test_invalid_age(self, validator):
        case = PatientCase(
            case_id="test",
            clinical_history=ClinicalHistory(
                age=200,  # Invalid
                extraction_confidence=0.95,
                schema_valid=True,
            ),
        )
        result = validator.validate_case(case)
        assert "clinical_history" in result["invalid_fields"]

    def test_empty_case(self, validator):
        case = PatientCase(case_id="test_empty")
        result = validator.validate_case(case)
        assert len(result["valid_fields"]) == 0
        assert len(result["invalid_fields"]) == 0
        assert len(result["validation_errors"]) == 0


# ── Extraction Confidence Gate Tests ─────────────────────────────────


class TestExtractionConfidenceGate:
    @pytest.fixture
    def gate(self):
        return ExtractionConfidenceGate()

    def test_accepted_threshold(self, gate):
        level = gate.gate_field("test", 0.95)
        assert level == ExtractionConfidenceLevel.ACCEPTED

    def test_accepted_above_threshold(self, gate):
        level = gate.gate_field("test", 0.99)
        assert level == ExtractionConfidenceLevel.ACCEPTED

    def test_flagged_threshold(self, gate):
        level = gate.gate_field("test", 0.90)
        assert level == ExtractionConfidenceLevel.FLAGGED

    def test_unknown_threshold(self, gate):
        level = gate.gate_field("test", 0.80)
        assert level == ExtractionConfidenceLevel.UNKNOWN

    def test_zero_confidence(self, gate):
        level = gate.gate_field("test", 0.0)
        assert level == ExtractionConfidenceLevel.UNKNOWN

    def test_gate_evidence_sets_levels(self, gate):
        case = PatientCase(
            case_id="test",
            troponin=TroponinEvidence(
                value=50.0, extraction_confidence=0.98, schema_valid=True,
            ),
            ecg=ECGEvidence(
                interpretation="normal", extraction_confidence=0.60, schema_valid=True,
            ),
        )
        gated = gate.gate_evidence(case)
        assert gated.troponin.confidence_level == ExtractionConfidenceLevel.ACCEPTED
        assert gated.ecg.confidence_level == ExtractionConfidenceLevel.UNKNOWN
        # ECG with UNKNOWN confidence should have schema_valid set to False
        assert gated.ecg.schema_valid == False


# ── Output Validator Tests ───────────────────────────────────────────


class TestOutputValidator:
    @pytest.fixture
    def validator(self):
        return OutputValidator()

    @pytest.fixture
    def sample_result(self):
        return ReasoningResult(
            state=EvidenceState.INCOMPLETE,
            supported_claims=["myocardial injury may be present"],
            unsupported_claims=["acute myocardial infarction is established"],
            missing_information=[
                MissingInformation(
                    field="serial_troponin",
                    reason_needed="Need rise/fall pattern",
                    askable=True,
                    ask_prompt="Repeat troponin in 3h",
                    criticality="REQUIRED",
                ),
            ],
            conflicts=[],
            source_trace=[
                SourceTraceEntry(
                    source_id="udmi_2018_injury",
                    source_name="Fourth Universal Definition of MI",
                    claim_supported="myocardial_injury_criterion",
                    reliability="HIGH",
                    recency_status="AGING",
                    applicability="APPLICABLE",
                ),
            ],
            reasons=["Serial troponin data missing"],
            condition_checks=[],
            conflict_status=ConflictStatus.NOT_ASSESSABLE,
            corroboration_status=CorroborationStatus.NOT_ASSESSABLE,
            generic_completeness=ConditionResult.PASS_RESULT,
            criteria_specific_completeness=ConditionResult.FAIL_RESULT,
        )

    def test_valid_explanation_passes(self, validator, sample_result):
        explanation = (
            "Evidence Assessment: INCOMPLETE\n\n"
            "The available evidence is incomplete. The serial_troponin data is missing, "
            "which is needed to assess the rise/fall pattern. "
            "Myocardial injury may be present but acute myocardial infarction is not established. "
            "Source: udmi_2018_injury."
        )
        passed, violations = validator.validate_explanation(explanation, sample_result)
        assert passed, f"Expected pass but got violations: {violations}"

    def test_missing_state_mention(self, validator, sample_result):
        explanation = "The patient has some troponin elevation."
        passed, violations = validator.validate_explanation(explanation, sample_result)
        assert not passed
        assert any("state" in v.lower() or "INCOMPLETE" in v for v in violations)

    def test_missing_info_not_mentioned(self, validator, sample_result):
        explanation = (
            "Evidence Assessment: INCOMPLETE\n\n"
            "The evidence is incomplete but we have troponin data."
        )
        passed, violations = validator.validate_explanation(explanation, sample_result)
        assert not passed
        assert any("serial_troponin" in v for v in violations)

    def test_template_fallback_always_valid(self, validator, sample_result):
        """Template fallback must always pass its own validation."""
        template = validator.generate_template_fallback(sample_result)
        passed, violations = validator.validate_explanation(template, sample_result)
        assert passed, f"Template fallback failed validation: {violations}"

    def test_template_mentions_state(self, validator, sample_result):
        template = validator.generate_template_fallback(sample_result)
        assert "INCOMPLETE" in template

    def test_template_mentions_missing_info(self, validator, sample_result):
        template = validator.generate_template_fallback(sample_result)
        assert "serial_troponin" in template

    def test_template_mentions_sources(self, validator, sample_result):
        template = validator.generate_template_fallback(sample_result)
        assert "udmi_2018_injury" in template
