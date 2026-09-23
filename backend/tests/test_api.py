"""
API Integration tests for FastAPI endpoints.
Tests /api/scenarios, /api/scenarios/{id}, /api/scenarios/{id}/analyze, /api/analyze.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from backend.schemas.patient_evidence import EvidenceState


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "Warrant" in data["system"]


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_scenarios(client):
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 6
    ids = [s["id"] for s in scenarios]
    assert ids == [1, 2, 3, 4, 5, 6]


def test_get_scenario_by_id(client):
    for sc_id in range(1, 7):
        res = client.get(f"/api/scenarios/{sc_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == sc_id
        assert "patient_case" in data


def test_analyze_all_scenarios(client):
    """Verify that all 6 demo scenarios analyze via the API and reach their exact target state."""
    target_states = {
        1: EvidenceState.SUFFICIENT,
        2: EvidenceState.ADDITIONAL_INFORMATION_REQUIRED,
        3: EvidenceState.CONFLICTING,
        4: EvidenceState.QUESTIONABLE,
        5: EvidenceState.NO_RELIABLE_CONCLUSION,
        6: EvidenceState.SUFFICIENT,
    }

    for sc_id, expected_state in target_states.items():
        res = client.post(f"/api/scenarios/{sc_id}/analyze")
        assert res.status_code == 200, f"Scenario {sc_id} failed: {res.text}"
        data = res.json()
        assert "analysis" in data
        assert "reasoning_result" in data["analysis"]
        actual_state = data["analysis"]["reasoning_result"]["state"]
        assert actual_state == expected_state.value, (
            f"Scenario {sc_id} expected {expected_state.value} but got {actual_state}"
        )


def test_custom_case_analysis(client):
    """Verify POST /api/analyze with a custom JSON case."""
    custom_case = {
        "case_id": "api_custom_001",
        "case_description": "Custom API test case",
        "troponin": {
            "value": 95.0,
            "unit": "ng/L",
            "timestamp": "2026-09-23T14:00:00Z",
            "assay": "Abbott Architect STAT High Sensitive Troponin-I",
            "serial_values": [
                {"value": 10.0, "timestamp": "2026-09-23T11:00:00Z"}
            ],
            "extraction_confidence": 0.98,
            "verification_status": "VERIFIED",
            "schema_valid": True
        },
        "ecg": {
            "interpretation": "ST depression in leads V4-V6",
            "st_elevation": False,
            "st_depression": True,
            "q_waves": False,
            "timestamp": "2026-09-23T11:15:00Z",
            "quality": "good",
            "extraction_confidence": 0.97,
            "verification_status": "VERIFIED",
            "schema_valid": True
        },
        "symptoms": {
            "chest_pain": True,
            "onset_time": "2026-09-23T10:00:00Z",
            "characteristics": "crushing",
            "duration_minutes": 60.0,
            "extraction_confidence": 0.96,
            "verification_status": "VERIFIED",
            "schema_valid": True
        },
        "clinical_history": {
            "age": 60,
            "sex": "male",
            "extraction_confidence": 0.95,
            "verification_status": "VERIFIED",
            "schema_valid": True
        },
        "timing": {
            "symptom_onset": "2026-09-23T10:00:00Z",
            "presentation_time": "2026-09-23T11:00:00Z",
            "onset_to_presentation_minutes": 60.0,
            "serial_sample_spacing_minutes": 180.0,
            "extraction_confidence": 0.96,
            "verification_status": "VERIFIED",
            "schema_valid": True
        }
    }

    res = client.post("/api/analyze", json=custom_case)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "api_custom_001"
    assert data["reasoning_result"]["state"] == "SUFFICIENT"
    assert len(data["reasoning_result"]["supported_claims"]) > 0
