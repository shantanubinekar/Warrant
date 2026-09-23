"""
Tests for the Deterministic Reasoning Engine (§3.6).

Runs all 6 demo scenarios through the real reasoning engine
and verifies each produces the correct evidence state.
Also tests edge cases and invariants.
"""

import pytest
from backend.engine.reasoning_engine import ReasoningEngine
from backend.knowledge.medical_knowledge_base import MedicalKnowledgeBase
from backend.scenarios.demo_cases import DemoScenarios
from backend.schemas.patient_evidence import (
    PatientCase, EvidenceState, ConditionResult, TroponinEvidence,
    ECGEvidence, SymptomsEvidence, ClinicalHistory, TimingEvidence,
    VerificationStatus,
)
from datetime import datetime


@pytest.fixture
def engine():
    return ReasoningEngine()


@pytest.fixture
def knowledge_base():
    return MedicalKnowledgeBase()


# ── Demo Scenario Tests ──────────────────────────────────────────────
# All 6 must run through the SAME reasoning engine — never hardcoded.


class TestDemoScenarios:
    """All 6 demo scenarios must produce their target evidence state."""

    def test_scenario_1_sufficient(self, engine, knowledge_base):
        """Complete AMI presentation → SUFFICIENT."""
        scenario = DemoScenarios.get_scenario(1)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        assert result.state == EvidenceState.SUFFICIENT
        assert len(result.supported_claims) > 0
        assert len(result.reasons) > 0

    def test_scenario_2_incomplete(self, engine, knowledge_base):
        """Missing serial troponin → INCOMPLETE or ADDITIONAL_INFORMATION_REQUIRED."""
        scenario = DemoScenarios.get_scenario(2)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        assert result.state in (
            EvidenceState.INCOMPLETE,
            EvidenceState.ADDITIONAL_INFORMATION_REQUIRED,
        )
        # Must identify serial troponin as missing
        missing_fields = [m.field for m in result.missing_information]
        assert any("serial" in f.lower() or "troponin" in f.lower() for f in missing_fields)

    def test_scenario_3_conflicting(self, engine, knowledge_base):
        """Conflicting guidelines → CONFLICTING."""
        scenario = DemoScenarios.get_scenario(3)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        assert result.state == EvidenceState.CONFLICTING
        assert len(result.conflicts) > 0

    def test_scenario_4_questionable(self, engine, knowledge_base):
        """Low extraction confidence → QUESTIONABLE."""
        scenario = DemoScenarios.get_scenario(4)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        assert result.state == EvidenceState.QUESTIONABLE

    def test_scenario_5_no_reliable_conclusion(self, engine, knowledge_base):
        """Unknown assay → NO_RELIABLE_CONCLUSION."""
        scenario = DemoScenarios.get_scenario(5)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        assert result.state == EvidenceState.NO_RELIABLE_CONCLUSION
        # Must flag assay as unknown
        assert any("assay" in r.lower() or "unknown" in r.lower() for r in result.reasons)

    def test_scenario_6_sufficient_single_source(self, engine, knowledge_base):
        """STEMI with single source → SUFFICIENT (alone ≠ weak)."""
        scenario = DemoScenarios.get_scenario(6)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        assert result.state == EvidenceState.SUFFICIENT
        assert len(result.supported_claims) > 0


# ── Core Engine Invariants ───────────────────────────────────────────


class TestEngineInvariants:
    """Test that the engine respects core architectural invariants."""

    def test_empty_case_is_incomplete(self, engine, knowledge_base):
        """A case with no evidence must be INCOMPLETE."""
        empty_case = PatientCase(case_id="test_empty")
        result = engine.reason(empty_case, knowledge_base)
        assert result.state in (
            EvidenceState.INCOMPLETE,
            EvidenceState.ADDITIONAL_INFORMATION_REQUIRED,
            EvidenceState.NO_RELIABLE_CONCLUSION,
        )
        assert len(result.missing_information) > 0

    def test_unknown_assay_never_guesses(self, engine, knowledge_base):
        """If assay is unknown, reference comparison must be UNKNOWN, never a guess."""
        case = PatientCase(
            case_id="test_unknown_assay",
            troponin=TroponinEvidence(
                value=50.0,
                unit="ng/L",
                timestamp=datetime(2026, 9, 23, 14, 0, 0),
                assay=None,  # Unknown assay
                extraction_confidence=0.98,
                verification_status=VerificationStatus.VERIFIED,
                schema_valid=True,
            ),
            clinical_history=ClinicalHistory(
                age=50, sex="male",
                extraction_confidence=0.95,
                schema_valid=True,
            ),
            timing=TimingEvidence(
                extraction_confidence=0.95,
                schema_valid=True,
            ),
        )
        result = engine.reason(case, knowledge_base)
        # Must NOT return SUFFICIENT — assay is unknown
        assert result.state != EvidenceState.SUFFICIENT
        # Must have UNKNOWN condition check for assay
        assay_checks = [
            c for c in result.condition_checks
            if "assay" in c.condition_name.lower()
        ]
        assert any(c.result == ConditionResult.UNKNOWN for c in assay_checks)

    def test_low_confidence_treated_as_unknown(self, engine, knowledge_base):
        """Troponin with confidence < 85% must be treated as UNKNOWN, not trusted."""
        case = PatientCase(
            case_id="test_low_confidence",
            troponin=TroponinEvidence(
                value=100.0,
                unit="ng/L",
                timestamp=datetime(2026, 9, 23, 14, 0, 0),
                assay="Abbott Architect STAT High Sensitive Troponin-I",
                extraction_confidence=0.50,  # Very low
                verification_status=VerificationStatus.UNVERIFIED,
                schema_valid=True,
            ),
            clinical_history=ClinicalHistory(
                age=60, sex="male",
                extraction_confidence=0.95,
                schema_valid=True,
            ),
        )
        result = engine.reason(case, knowledge_base)
        # Must NOT return SUFFICIENT — extraction confidence too low
        assert result.state != EvidenceState.SUFFICIENT

    def test_pass_fail_unknown_never_boolean(self, engine, knowledge_base):
        """Every condition check uses PASS/FAIL/UNKNOWN, never plain true/false."""
        scenario = DemoScenarios.get_scenario(1)
        result = engine.reason(scenario["patient_case"], knowledge_base)
        for check in result.condition_checks:
            assert check.result in (
                ConditionResult.PASS_RESULT,
                ConditionResult.FAIL_RESULT,
                ConditionResult.UNKNOWN,
            )

    def test_state_and_action_are_separate(self, engine, knowledge_base):
        """ReasoningResult has state; action is mapped separately."""
        from backend.engine.state_action_mapper import StateActionMapper
        mapper = StateActionMapper()

        for scenario_id in range(1, 7):
            scenario = DemoScenarios.get_scenario(scenario_id)
            result = engine.reason(scenario["patient_case"], knowledge_base)
            action = mapper.map_state_to_action(result.state, result)

            # State and action must both be present but separate
            assert result.state is not None
            assert action.action is not None
            assert action.state == result.state

    def test_all_scenarios_have_reasons(self, engine, knowledge_base):
        """Every scenario must produce at least one reason."""
        for scenario_id in range(1, 7):
            scenario = DemoScenarios.get_scenario(scenario_id)
            result = engine.reason(scenario["patient_case"], knowledge_base)
            assert len(result.reasons) > 0, f"Scenario {scenario_id} has no reasons"

    def test_all_scenarios_have_source_trace(self, engine, knowledge_base):
        """Every scenario with evidence must have a source trace."""
        for scenario_id in range(1, 7):
            scenario = DemoScenarios.get_scenario(scenario_id)
            result = engine.reason(scenario["patient_case"], knowledge_base)
            # Source trace may be empty only if no applicable sources found
            # but in our demo scenarios, all have cardiac evidence
            assert len(result.source_trace) > 0, f"Scenario {scenario_id} has no source trace"
