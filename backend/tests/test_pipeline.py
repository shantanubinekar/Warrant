"""
Tests for the Pipeline Orchestrator — end-to-end pipeline tests.

Uses template fallback (no LLM) to test the full pipeline
from PatientCase → AnalysisResponse.
"""

import pytest
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.scenarios.demo_cases import DemoScenarios
from backend.schemas.patient_evidence import EvidenceState, PatientCase


@pytest.fixture
def pipeline():
    """Pipeline without LLM — uses template fallback."""
    return PipelineOrchestrator(llm_client=None)


class TestPipelineEndToEnd:
    """End-to-end pipeline tests with template fallback."""

    def test_all_scenarios_produce_analysis_response(self, pipeline):
        """Every demo scenario must produce a valid AnalysisResponse."""
        for scenario_id in range(1, 7):
            scenario = DemoScenarios.get_scenario(scenario_id)
            response = pipeline.run_pipeline(scenario["patient_case"])

            assert response.case_id == scenario["patient_case"].case_id
            assert response.reasoning_result is not None
            assert response.action is not None
            assert response.explanation is not None
            assert len(response.explanation) > 0
            assert response.explanation_source == "template"  # no LLM
            assert response.timestamp is not None

    def test_pipeline_trace_present(self, pipeline):
        """Pipeline trace must be included in the response."""
        scenario = DemoScenarios.get_scenario(1)
        response = pipeline.run_pipeline(scenario["patient_case"])

        assert response.pipeline_trace is not None
        assert "pipeline_stages" in response.pipeline_trace
        stages = response.pipeline_trace["pipeline_stages"]
        assert len(stages) >= 6  # At least 6 stages in the pipeline

    def test_template_fallback_mentions_state(self, pipeline):
        """Template explanation must mention the evidence state."""
        for scenario_id in range(1, 7):
            scenario = DemoScenarios.get_scenario(scenario_id)
            response = pipeline.run_pipeline(scenario["patient_case"])

            state_value = response.reasoning_result.state.value
            assert state_value in response.explanation, (
                f"Scenario {scenario_id}: template explanation doesn't mention state '{state_value}'"
            )

    def test_template_mentions_missing_info(self, pipeline):
        """If there's missing info, template must mention it."""
        # Scenario 2 has missing serial troponin
        scenario = DemoScenarios.get_scenario(2)
        response = pipeline.run_pipeline(scenario["patient_case"])

        if response.reasoning_result.missing_information:
            assert "Missing Information" in response.explanation or "missing" in response.explanation.lower()

    def test_empty_case_pipeline(self, pipeline):
        """Empty case must complete pipeline without crashing."""
        empty_case = PatientCase(case_id="test_pipeline_empty")
        response = pipeline.run_pipeline(empty_case)

        assert response is not None
        assert response.reasoning_result.state in (
            EvidenceState.INCOMPLETE,
            EvidenceState.ADDITIONAL_INFORMATION_REQUIRED,
            EvidenceState.NO_RELIABLE_CONCLUSION,
        )

    def test_action_matches_state(self, pipeline):
        """Action state must match reasoning result state."""
        for scenario_id in range(1, 7):
            scenario = DemoScenarios.get_scenario(scenario_id)
            response = pipeline.run_pipeline(scenario["patient_case"])

            assert response.action.state == response.reasoning_result.state, (
                f"Scenario {scenario_id}: action state mismatch"
            )
