"""
Comprehensive test suite for the refactored evidence-aware clinical decision support system.

Validates the 9 specific requirements:
1. SUFFICIENT (complete presentation -> SUFFICIENT)
2. MISSING ≠ FAIL (ConditionResult.UNKNOWN vs FAIL_RESULT)
3. CONFLICT (conflicting guidelines -> CONFLICTING without picking a side)
4. QUESTIONABLE (low quality/confidence -> QUESTIONABLE)
5. WEAKER_CLAIM_ONLY (evidence supports only weaker claim e.g. myocardial injury without ischemia)
6. RULE_NOT_AVAILABLE (out-of-scope condition -> RULE_NOT_AVAILABLE; no retrieval or reasoning invoked)
7. Multi-domain retrieval (domain-restricted, max searches, fallback query)
8. Structural test (new claim with condition tree evaluated with zero engine changes)
9. LLM explanation cannot exceed reasoning state (output validator enforces authoritative state)
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from backend.engine.reasoning_engine import ReasoningEngine
from backend.knowledge.medical_knowledge_base import MedicalKnowledgeBase
from backend.knowledge.claim_registry import ClaimRegistry
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.retrieval.retrieval_manager import RetrievalManager, MAX_TOTAL_SEARCHES
from backend.validators.output_validator import OutputValidator
from backend.scenarios.demo_cases import DemoScenarios
from backend.schemas.patient_evidence import (
    PatientCase, EvidenceState, ConditionResult, TroponinEvidence,
    ECGEvidence, SymptomsEvidence, ImagingEvidence, ClinicalHistory, TimingEvidence,
    VerificationStatus, ConflictStatus, CorroborationStatus,
)
from backend.schemas.medical_knowledge import (
    StructuredClaim, ConditionNode, SourceCondition,
)
from backend.schemas.engine_output import ReasoningResult, MissingInformation


@pytest.fixture
def engine():
    return ReasoningEngine()


@pytest.fixture
def kb():
    return MedicalKnowledgeBase()


@pytest.fixture
def registry():
    return ClaimRegistry()


# ── 1. SUFFICIENT ────────────────────────────────────────────────────────────

def test_sufficient(engine, kb):
    """Complete presentation with troponin rise/fall and ischemic ECG -> SUFFICIENT."""
    scenario = DemoScenarios.get_scenario(1)
    result = engine.reason(scenario["patient_case"], kb)
    assert result.state == EvidenceState.SUFFICIENT
    assert len(result.supported_claims) > 0
    assert any("myocardial" in c.lower() or "infarction" in c.lower() for c in result.supported_claims)
    assert len(result.source_trace) > 0


# ── 2. MISSING ≠ FAIL ────────────────────────────────────────────────────────

def test_missing_not_equal_to_fail(engine, kb):
    """Missing evidence yields UNKNOWN condition check and INCOMPLETE / ADDITIONAL_INFO, NOT FAIL_RESULT."""
    scenario = DemoScenarios.get_scenario(2)
    case = scenario["patient_case"]
    result = engine.reason(case, kb)

    # Must NOT fail the serial check — it must be UNKNOWN
    serial_checks = [c for c in result.condition_checks if "serial" in c.condition_name.lower()]
    assert len(serial_checks) > 0
    assert any(c.result == ConditionResult.UNKNOWN for c in serial_checks)
    assert not any(c.result == ConditionResult.FAIL_RESULT for c in serial_checks)

    # State must be incomplete or additional info required, never failed/rejected
    assert result.state in (EvidenceState.INCOMPLETE, EvidenceState.ADDITIONAL_INFORMATION_REQUIRED)


# ── 3. CONFLICT ──────────────────────────────────────────────────────────────

def test_conflict(engine, kb):
    """Conflicting guideline algorithms yield CONFLICTING state without picking a side."""
    scenario = DemoScenarios.get_scenario(3)
    result = engine.reason(scenario["patient_case"], kb)
    assert result.state == EvidenceState.CONFLICTING
    assert len(result.conflicts) > 0
    # Engine must report both positions and not pick one
    conflict = result.conflicts[0]
    assert conflict.source_a is not None
    assert conflict.source_b is not None
    assert not conflict.resolution_possible


# ── 4. QUESTIONABLE ──────────────────────────────────────────────────────────

def test_questionable(engine, kb):
    """Low quality or unverified evidence yields QUESTIONABLE state."""
    scenario = DemoScenarios.get_scenario(4)
    result = engine.reason(scenario["patient_case"], kb)
    assert result.state == EvidenceState.QUESTIONABLE
    assert any("questionable" in r.lower() for r in result.reasons)


# ── 5. WEAKER_CLAIM_ONLY ─────────────────────────────────────────────────────

def test_weaker_claim_only(engine, kb):
    """When troponin criteria pass (myocardial injury) but clinical ischemia is absent, state is WEAKER_CLAIM_ONLY."""
    case = PatientCase(
        case_id="test_injury_only",
        case_description="Elevated troponin with rise/fall, but no ischemic symptoms or ECG changes",
        troponin=TroponinEvidence(
            value=65.0,
            unit="ng/L",
            assay="Abbott Architect STAT High Sensitive Troponin-I",
            serial_values=[
                {"value": 10.0, "timestamp": "2026-09-23T11:00:00Z"},
                {"value": 45.0, "timestamp": "2026-09-23T12:30:00Z"},
            ],
            extraction_confidence=0.98,
            verification_status=VerificationStatus.VERIFIED,
            schema_valid=True,
        ),
        ecg=ECGEvidence(
            interpretation="Normal sinus rhythm, no ischemic ST-T changes",
            st_elevation=False,
            st_depression=False,
            q_waves=False,
            quality="good",
            extraction_confidence=0.97,
            verification_status=VerificationStatus.VERIFIED,
            schema_valid=True,
        ),
        symptoms=SymptomsEvidence(
            chest_pain=False,  # No chest pain
            extraction_confidence=0.96,
            verification_status=VerificationStatus.VERIFIED,
            schema_valid=True,
        ),
        imaging=ImagingEvidence(
            modality="echo",
            finding="Normal wall motion, no ischemic changes",
            wall_motion_abnormality=False,
            extraction_confidence=0.96,
            verification_status=VerificationStatus.VERIFIED,
            schema_valid=True,
        ),
        clinical_history=ClinicalHistory(
            age=62, sex="male",
            extraction_confidence=0.95,
            verification_status=VerificationStatus.VERIFIED,
            schema_valid=True,
        ),
        timing=TimingEvidence(
            serial_sample_spacing_minutes=180.0,
            extraction_confidence=0.96,
            verification_status=VerificationStatus.VERIFIED,
            schema_valid=True,
        ),
    )

    result = engine.reason(case, kb)
    assert result.state == EvidenceState.WEAKER_CLAIM_ONLY
    # Myocardial injury must be supported
    assert any("myocardial injury" in c.lower() for c in result.supported_claims)
    # AMI Type 1 / NSTEMI must be in unsupported claims
    assert any("type 1 ami" in c.lower() or "nstemi" in c.lower() for c in result.unsupported_claims)


# ── 6. RULE_NOT_AVAILABLE (No Retrieval, No Reasoning) ───────────────────────

def test_rule_not_available_no_retrieval_no_reasoning():
    """An out-of-scope condition triggers RULE_NOT_AVAILABLE BEFORE retrieval or reasoning is invoked."""
    orchestrator = PipelineOrchestrator(llm_client=None)

    # Mock the retrieval manager and reasoning engine to ensure they are NOT invoked
    orchestrator.retrieval_manager.retrieve_for_claim = MagicMock()
    orchestrator.reasoning_engine.reason = MagicMock()

    case = PatientCase(
        case_id="test_unsupported_condition",
        case_description="Patient presenting with right lower quadrant abdominal pain",
        target_condition="acute_appendicitis",
    )

    response = orchestrator.run_pipeline(case)

    # Must be RULE_NOT_AVAILABLE
    assert response.reasoning_result.state == EvidenceState.RULE_NOT_AVAILABLE
    # Retrieval and reasoning engine must NOT have been called
    assert orchestrator.retrieval_manager.retrieve_for_claim.call_count == 0
    assert orchestrator.reasoning_engine.reason.call_count == 0

    # Response must explain what IS covered
    assert "Covered" in response.explanation or "validated" in response.explanation.lower()
    assert any("myocardial" in r.lower() or "ami" in r.lower() for r in response.reasoning_result.reasons)


# ── 7. Multi-Domain Retrieval ────────────────────────────────────────────────

def test_multi_domain_retrieval():
    """RetrievalManager queries trusted domains, reformulates on empty results, and respects search cap."""
    mock_searcher = MagicMock()
    # First search returns empty, second search (broader) returns results
    mock_searcher.available = True
    mock_searcher.search.return_value = []
    mock_searcher.search_trusted.return_value = [
        {
            "title": "2020 ESC NSTE-ACS Guidelines",
            "snippet": "Serial troponin measurement is essential in acute myocardial infarction.",
            "url": "https://www.escardio.org/guidelines",
            "domain": "escardio.org",
        }
    ]

    manager = RetrievalManager(searcher=mock_searcher)
    claim = StructuredClaim(
        claim_id="test_claim",
        claim_type="test_claim",
        description="Troponin elevation in AMI",
        conditions=[],
        supporting_sources=[],
        population="adult",
        required_evidence=["troponin"],
        claim_text="Troponin elevation criterion",
    )

    citations = manager.retrieve_for_claim(claim)

    assert len(citations) == 1
    assert citations[0].domain == "escardio.org"
    assert citations[0].relevance == "HIGH"
    # Round 1 (search) + Round 2 (search_trusted fallback) = 2 searches
    assert manager.search_count == 2
    assert manager.search_count <= MAX_TOTAL_SEARCHES


# ── 8. Structural Test: New Claim with Zero Engine Changes ────────────────────

def test_structural_new_claim_zero_engine_changes(engine, kb):
    """Adding a new structured claim with a condition tree evaluates seamlessly without changing engine code."""
    # Define a new, hypothetical clinical claim with compound AND/OR condition tree
    new_claim = StructuredClaim(
        claim_id="new_pericarditis_claim",
        claim_type="acute_pericarditis",
        description="Acute pericarditis: chest pain plus PR depression or ST elevation",
        conditions=[
            SourceCondition(
                marker="chest_pain",
                comparison="==",
                reference="pleuritic_chest_pain",
            )
        ],
        supporting_sources=[],
        population="adult",
        required_evidence=["symptoms", "ecg"],
        claim_text="Acute pericarditis diagnosis criterion",
        strength_rank=2,
        condition_tree=ConditionNode(
            type="AND",
            children=[
                ConditionNode(type="CONDITION", check="PRESENT", evidence_type="symptoms", field="chest_pain"),
                ConditionNode(
                    type="OR",
                    children=[
                        ConditionNode(type="CONDITION", check="PRESENT", evidence_type="ecg", field="st_elevation"),
                        ConditionNode(type="CONDITION", check="PRESENT", evidence_type="ecg", field="st_depression"),
                    ]
                )
            ]
        )
    )

    case = PatientCase(
        case_id="test_new_disease",
        symptoms=SymptomsEvidence(chest_pain=True, extraction_confidence=0.98, schema_valid=True),
        ecg=ECGEvidence(interpretation="ST elevation", st_elevation=True, extraction_confidence=0.98, schema_valid=True),
    )

    condition_checks = []
    reasons = []

    # Call the generic evaluate_claim method
    result = engine.evaluate_claim(new_claim, case, kb, condition_checks, reasons)
    assert result == ConditionResult.PASS_RESULT
    assert len(condition_checks) > 0


# ── 9. LLM Explanation Cannot Exceed Reasoning State ─────────────────────────

def test_llm_explanation_cannot_exceed_reasoning_state():
    """OutputValidator rejects an LLM explanation asserting claims not supported by the engine."""
    validator = OutputValidator()

    # Engine decided INCOMPLETE, with AMI unsupported
    engine_result = ReasoningResult(
        state=EvidenceState.INCOMPLETE,
        supported_claims=["myocardial injury may be present"],
        unsupported_claims=["acute myocardial infarction is confirmed"],
        missing_information=[
            MissingInformation(field="serial_troponin", reason_needed="Need serial rise/fall pattern")
        ],
        conflicts=[],
        source_trace=[],
        reasons=["Serial data missing"],
        condition_checks=[],
        conflict_status=ConflictStatus.NOT_ASSESSABLE,
        corroboration_status=CorroborationStatus.NOT_ASSESSABLE,
        generic_completeness=ConditionResult.PASS_RESULT,
        criteria_specific_completeness=ConditionResult.FAIL_RESULT,
    )

    # Hallucinated LLM explanation claiming AMI is confirmed (violating unsupported_claims)
    overstepping_explanation = (
        "Evidence Assessment: INCOMPLETE\n"
        "However, acute myocardial infarction is confirmed by the presentation.\n"
        "Serial_troponin is missing."
    )

    passed, violations = validator.validate_explanation(overstepping_explanation, engine_result)
    assert not passed
    assert any("unsupported claim" in v.lower() for v in violations)


# ── 10. Claim Domain Identification Short-Circuit (Regression Tests) ─────────

def test_out_of_scope_text_short_circuits_without_extraction_or_reasoning():
    """An out-of-scope note (oncology) is identified as 'unknown', and NEVER calls

    extract_evidence(), get_applicable_claims(), or reasoning_engine.reason().
    """
    from backend.api.routes import analysis

    oncology_note = (
        "A 61-year-old male presents with unintentional weight loss of 8 kg over 3 months, "
        "persistent cough, and hemoptysis. CT chest reveals a 4.2 cm spiculated mass in the "
        "right upper lobe with mediastinal lymphadenopathy. PET-CT shows FDG-avid uptake, "
        "concerning for locally advanced non-small cell lung cancer. No distant metastases identified."
    )

    mock_llm = MagicMock()
    # 1. identify_claim_domain returns 'unknown'
    mock_llm.identify_claim_domain.return_value = "unknown"
    mock_llm.extract_evidence = MagicMock()

    # 2. Spy / mock pipeline components
    orig_llm = analysis.llm_client
    orig_pipeline = analysis.pipeline

    try:
        analysis.llm_client = mock_llm
        test_pipeline = PipelineOrchestrator(llm_client=mock_llm, enable_retrieval=False)
        test_pipeline.knowledge_base.get_applicable_claims = MagicMock()
        test_pipeline.reasoning_engine.reason = MagicMock()
        analysis.pipeline = test_pipeline

        # Run upload analysis
        result = analysis._extract_and_analyze(oncology_note, case_description="Oncology note")

        # 3. Assert extract_evidence was NEVER called
        assert mock_llm.extract_evidence.call_count == 0

        # 4. Assert retrieval / get_applicable_claims was NEVER called
        assert test_pipeline.knowledge_base.get_applicable_claims.call_count == 0

        # 5. Assert reasoning engine was NEVER called
        assert test_pipeline.reasoning_engine.reason.call_count == 0

        # 6. Assert response is RULE_NOT_AVAILABLE
        assert result["analysis"]["reasoning_result"]["state"] == "RULE_NOT_AVAILABLE"
        assert result["extracted_case"]["target_condition"] == "unknown"
        assert "RULE_NOT_AVAILABLE" in result["analysis"]["explanation"]

    finally:
        analysis.llm_client = orig_llm
        analysis.pipeline = orig_pipeline


def test_in_scope_ami_text_proceeds_through_extraction_and_pipeline():
    """An AMI note is identified as 'ami', and DOES call extract_evidence and the pipeline."""
    from backend.api.routes import analysis

    ami_note = (
        "A 58-year-old male presents with severe crushing substernal chest pain radiating to left arm. "
        "ECG shows 3mm ST elevation in leads V1-V4. Troponin I is 85 ng/L (Abbott)."
    )

    mock_llm = MagicMock()
    mock_llm.identify_claim_domain.return_value = "ami"
    mock_case = DemoScenarios.get_scenario(1)["patient_case"].model_copy(deep=True)
    mock_llm.extract_evidence.return_value = mock_case

    orig_llm = analysis.llm_client
    orig_pipeline = analysis.pipeline

    try:
        analysis.llm_client = mock_llm
        test_pipeline = PipelineOrchestrator(llm_client=mock_llm, enable_retrieval=False)
        analysis.pipeline = test_pipeline

        result = analysis._extract_and_analyze(ami_note, case_description="AMI presentation")

        # Must have called extract_evidence
        assert mock_llm.extract_evidence.call_count == 1
        assert result["extracted_case"]["target_condition"] == "ami"
        assert result["analysis"]["reasoning_result"]["state"] == "SUFFICIENT"

    finally:
        analysis.llm_client = orig_llm
        analysis.pipeline = orig_pipeline

