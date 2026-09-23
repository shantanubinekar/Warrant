"""
Demo Scenarios (§7) — 6 predefined cases, one per target state.

ALL scenarios run through the SAME ReasoningEngine — no hardcoded returns.
Each case is a PatientCase with specific evidence designed to trigger
a specific evidence state through the real reasoning pipeline.
"""

from datetime import datetime
from typing import List, Dict, Any

from backend.schemas.patient_evidence import (
    PatientCase, TroponinEvidence, ECGEvidence, SymptomsEvidence,
    ImagingEvidence, ClinicalHistory, LabContext, TimingEvidence,
    DocumentQuality, VerificationStatus,
)


class DemoScenarios:
    """6 demo cases, each targeting a specific evidence state.

    All run through the SAME reasoning engine — never hardcoded.
    """

    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """Return all 6 demo scenarios."""
        return [
            DemoScenarios.get_scenario(i) for i in range(1, 7)
        ]

    @staticmethod
    def get_scenario(scenario_id: int) -> Dict[str, Any]:
        """Get a specific scenario by ID (1-6)."""
        scenarios = {
            1: DemoScenarios._scenario_1_sufficient,
            2: DemoScenarios._scenario_2_incomplete,
            3: DemoScenarios._scenario_3_conflicting,
            4: DemoScenarios._scenario_4_questionable,
            5: DemoScenarios._scenario_5_no_reliable_conclusion,
            6: DemoScenarios._scenario_6_sufficient_single_source,
        }
        builder = scenarios.get(scenario_id)
        if not builder:
            raise ValueError(f"Unknown scenario ID: {scenario_id}. Valid: 1-6")
        return builder()

    # ── Scenario 1: SUFFICIENT ───────────────────────────────────────

    @staticmethod
    def _scenario_1_sufficient() -> Dict[str, Any]:
        return {
            "id": 1,
            "title": "Complete AMI Presentation",
            "description": (
                "62-year-old male with crushing chest pain, serial troponin showing "
                "clear rise pattern (known assay: Abbott hs-cTnI), and ECG with "
                "ST depression. All evidence is high quality with known provenance."
            ),
            "target_state": "SUFFICIENT",
            "patient_case": PatientCase(
                case_id="demo_001_sufficient",
                case_description="Complete AMI presentation with all evidence present and high quality",
                troponin=TroponinEvidence(
                    value=85.0,
                    unit="ng/L",
                    timestamp=datetime(2026, 9, 23, 14, 0, 0),
                    assay="Abbott Architect STAT High Sensitive Troponin-I",
                    serial_values=[
                        {"value": 5.0, "timestamp": "2026-09-23T11:00:00Z"},
                        {"value": 42.0, "timestamp": "2026-09-23T12:30:00Z"},
                    ],
                    extraction_confidence=0.98,
                    extraction_source="lab_report_001",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                ecg=ECGEvidence(
                    interpretation="ST depression in leads V4-V6, consistent with ischemia",
                    st_elevation=False,
                    st_depression=True,
                    q_waves=False,
                    timestamp=datetime(2026, 9, 23, 11, 15, 0),
                    quality="good",
                    extraction_confidence=0.97,
                    extraction_source="ecg_report_001",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                symptoms=SymptomsEvidence(
                    chest_pain=True,
                    onset_time=datetime(2026, 9, 23, 10, 0, 0),
                    characteristics="crushing, substernal pressure",
                    duration_minutes=90.0,
                    radiation="left arm and jaw",
                    associated_symptoms=["diaphoresis", "dyspnea", "nausea"],
                    extraction_confidence=0.96,
                    extraction_source="clinical_notes_001",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                clinical_history=ClinicalHistory(
                    age=62,
                    sex="male",
                    diabetes=True,
                    hypertension=True,
                    smoking=False,
                    prior_mi=False,
                    prior_pci=False,
                    family_history_cad=True,
                    extraction_confidence=0.95,
                    extraction_source="medical_records_001",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                timing=TimingEvidence(
                    symptom_onset=datetime(2026, 9, 23, 10, 0, 0),
                    presentation_time=datetime(2026, 9, 23, 11, 0, 0),
                    onset_to_presentation_minutes=60.0,
                    serial_sample_spacing_minutes=180.0,
                    extraction_confidence=0.96,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
            ),
        }

    # ── Scenario 2: INCOMPLETE / ADDITIONAL_INFORMATION_REQUIRED ─────

    @staticmethod
    def _scenario_2_incomplete() -> Dict[str, Any]:
        return {
            "id": 2,
            "title": "Missing Serial Troponin",
            "description": (
                "55-year-old female with a single elevated troponin value (40 ng/L, "
                "known assay) but no serial data. The criterion requires a rise/fall "
                "pattern to establish myocardial injury. ECG shows non-specific changes."
            ),
            "target_state": "ADDITIONAL_INFORMATION_REQUIRED",
            "patient_case": PatientCase(
                case_id="demo_002_incomplete",
                case_description="Single troponin without serial data — cannot assess rise/fall",
                troponin=TroponinEvidence(
                    value=40.0,
                    unit="ng/L",
                    timestamp=datetime(2026, 9, 23, 14, 0, 0),
                    assay="Abbott Architect STAT High Sensitive Troponin-I",
                    serial_values=None,  # No serial data
                    extraction_confidence=0.97,
                    extraction_source="lab_report_002",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                ecg=ECGEvidence(
                    interpretation="Non-specific ST-T wave changes",
                    st_elevation=False,
                    st_depression=False,
                    q_waves=False,
                    timestamp=datetime(2026, 9, 23, 14, 10, 0),
                    quality="good",
                    extraction_confidence=0.96,
                    extraction_source="ecg_report_002",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                symptoms=SymptomsEvidence(
                    chest_pain=True,
                    onset_time=datetime(2026, 9, 23, 12, 0, 0),
                    characteristics="atypical, burning sensation",
                    duration_minutes=120.0,
                    extraction_confidence=0.95,
                    extraction_source="clinical_notes_002",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                clinical_history=ClinicalHistory(
                    age=55,
                    sex="female",
                    diabetes=False,
                    hypertension=True,
                    extraction_confidence=0.96,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                timing=TimingEvidence(
                    symptom_onset=datetime(2026, 9, 23, 12, 0, 0),
                    presentation_time=datetime(2026, 9, 23, 14, 0, 0),
                    onset_to_presentation_minutes=120.0,
                    extraction_confidence=0.96,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
            ),
        }

    # ── Scenario 3: CONFLICTING ──────────────────────────────────────

    @staticmethod
    def _scenario_3_conflicting() -> Dict[str, Any]:
        return {
            "id": 3,
            "title": "Conflicting Guideline Algorithms",
            "description": (
                "48-year-old male with troponin delta of 8 ng/L over 1 hour (known assay). "
                "ESC 0h/1h algorithm says this delta is sufficient for rule-in. "
                "ESC 2015 0h/3h algorithm requires a 3-hour sample with 20% delta. "
                "Two authoritative sources materially disagree on the required protocol."
            ),
            "target_state": "CONFLICTING",
            "patient_case": PatientCase(
                case_id="demo_003_conflicting",
                case_description="Sources disagree on serial timing algorithm (1h vs 3h)",
                troponin=TroponinEvidence(
                    value=20.0,
                    unit="ng/L",
                    timestamp=datetime(2026, 9, 23, 15, 0, 0),
                    assay="Abbott Architect STAT High Sensitive Troponin-I",
                    serial_values=[
                        {"value": 12.0, "timestamp": "2026-09-23T14:00:00Z"},
                    ],
                    extraction_confidence=0.98,
                    extraction_source="lab_report_003",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                ecg=ECGEvidence(
                    interpretation="ST depression in leads II, III, aVF",
                    st_elevation=False,
                    st_depression=True,
                    q_waves=False,
                    timestamp=datetime(2026, 9, 23, 14, 5, 0),
                    quality="good",
                    extraction_confidence=0.97,
                    extraction_source="ecg_report_003",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                symptoms=SymptomsEvidence(
                    chest_pain=True,
                    onset_time=datetime(2026, 9, 23, 13, 0, 0),
                    characteristics="pressure, retrosternal",
                    duration_minutes=60.0,
                    associated_symptoms=["diaphoresis"],
                    extraction_confidence=0.96,
                    extraction_source="clinical_notes_003",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                clinical_history=ClinicalHistory(
                    age=48,
                    sex="male",
                    diabetes=False,
                    hypertension=False,
                    smoking=True,
                    extraction_confidence=0.95,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                timing=TimingEvidence(
                    symptom_onset=datetime(2026, 9, 23, 13, 0, 0),
                    presentation_time=datetime(2026, 9, 23, 14, 0, 0),
                    onset_to_presentation_minutes=60.0,
                    serial_sample_spacing_minutes=60.0,
                    extraction_confidence=0.96,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
            ),
        }

    # ── Scenario 4: QUESTIONABLE ─────────────────────────────────────

    @staticmethod
    def _scenario_4_questionable() -> Dict[str, Any]:
        return {
            "id": 4,
            "title": "Low Quality Evidence",
            "description": (
                "70-year-old patient with troponin from a poorly scanned lab report "
                "(OCR confidence 60%, extraction confidence 80%). ECG is also from a "
                "poor quality scan. Evidence exists but is not trustworthy enough "
                "for a reliable clinical assessment."
            ),
            "target_state": "QUESTIONABLE",
            "patient_case": PatientCase(
                case_id="demo_004_questionable",
                case_description="Evidence present but extraction confidence below usable threshold",
                troponin=TroponinEvidence(
                    value=65.0,
                    unit="ng/L",
                    timestamp=datetime(2026, 9, 23, 10, 0, 0),
                    assay="Abbott Architect STAT High Sensitive Troponin-I",
                    serial_values=[
                        {"value": 30.0, "timestamp": "2026-09-23T07:00:00Z"},
                    ],
                    extraction_confidence=0.80,  # Below 85% threshold
                    extraction_source="scanned_report_004",
                    verification_status=VerificationStatus.UNVERIFIED,
                    schema_valid=True,
                ),
                ecg=ECGEvidence(
                    interpretation="Possible ST changes, image quality poor",
                    st_elevation=False,
                    st_depression=True,
                    timestamp=datetime(2026, 9, 23, 10, 15, 0),
                    quality="poor",
                    extraction_confidence=0.60,  # Very low
                    extraction_source="scanned_ecg_004",
                    verification_status=VerificationStatus.UNVERIFIED,
                    schema_valid=True,
                ),
                symptoms=SymptomsEvidence(
                    chest_pain=True,
                    onset_time=datetime(2026, 9, 23, 8, 0, 0),
                    characteristics="chest tightness",
                    extraction_confidence=0.90,
                    extraction_source="clinical_notes_004",
                    verification_status=VerificationStatus.UNVERIFIED,
                    schema_valid=True,
                ),
                clinical_history=ClinicalHistory(
                    age=70,
                    sex="male",
                    diabetes=True,
                    hypertension=True,
                    prior_mi=True,
                    extraction_confidence=0.88,
                    verification_status=VerificationStatus.UNVERIFIED,
                    schema_valid=True,
                ),
                timing=TimingEvidence(
                    symptom_onset=datetime(2026, 9, 23, 8, 0, 0),
                    presentation_time=datetime(2026, 9, 23, 10, 0, 0),
                    onset_to_presentation_minutes=120.0,
                    extraction_confidence=0.85,
                    verification_status=VerificationStatus.UNVERIFIED,
                    schema_valid=True,
                ),
                document_quality=DocumentQuality(
                    document_type="scanned_lab_report",
                    ocr_confidence=0.60,
                    legibility="poor",
                    source_file="scan_004.pdf",
                ),
            ),
        }

    # ── Scenario 5: NO_RELIABLE_CONCLUSION → Escalate ────────────────

    @staticmethod
    def _scenario_5_no_reliable_conclusion() -> Dict[str, Any]:
        return {
            "id": 5,
            "title": "Unknown Assay — Cannot Compare",
            "description": (
                "58-year-old with troponin value of 55 ng/L, but the assay is "
                "'Siemens Atellica IM hs-cTnI' — not in the reference database. "
                "Without knowing the 99th percentile URL for this specific assay, "
                "no reference comparison is possible. Result: UNKNOWN, not a guess."
            ),
            "target_state": "NO_RELIABLE_CONCLUSION",
            "patient_case": PatientCase(
                case_id="demo_005_no_conclusion",
                case_description="Assay not in reference database — comparison impossible",
                troponin=TroponinEvidence(
                    value=55.0,
                    unit="ng/L",
                    timestamp=datetime(2026, 9, 23, 16, 0, 0),
                    assay="Siemens Atellica IM hs-cTnI",  # Not in our reference DB
                    serial_values=[
                        {"value": 25.0, "timestamp": "2026-09-23T13:00:00Z"},
                    ],
                    extraction_confidence=0.98,
                    extraction_source="lab_report_005",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                ecg=ECGEvidence(
                    interpretation="Normal sinus rhythm, no acute changes",
                    st_elevation=False,
                    st_depression=False,
                    q_waves=False,
                    timestamp=datetime(2026, 9, 23, 13, 10, 0),
                    quality="good",
                    extraction_confidence=0.97,
                    extraction_source="ecg_report_005",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                symptoms=SymptomsEvidence(
                    chest_pain=True,
                    onset_time=datetime(2026, 9, 23, 12, 0, 0),
                    characteristics="atypical, epigastric discomfort",
                    duration_minutes=60.0,
                    extraction_confidence=0.95,
                    extraction_source="clinical_notes_005",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                clinical_history=ClinicalHistory(
                    age=58,
                    sex="male",
                    diabetes=False,
                    hypertension=True,
                    smoking=True,
                    extraction_confidence=0.96,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                timing=TimingEvidence(
                    symptom_onset=datetime(2026, 9, 23, 12, 0, 0),
                    presentation_time=datetime(2026, 9, 23, 13, 0, 0),
                    onset_to_presentation_minutes=60.0,
                    serial_sample_spacing_minutes=180.0,
                    extraction_confidence=0.96,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
            ),
        }

    # ── Scenario 6: SUFFICIENT (single source) ──────────────────────

    @staticmethod
    def _scenario_6_sufficient_single_source() -> Dict[str, Any]:
        return {
            "id": 6,
            "title": "STEMI — Single Authoritative Source",
            "description": (
                "45-year-old male with acute chest pain and ECG showing clear "
                "ST elevation in leads V1-V4. Troponin is elevated with known assay. "
                "Only ONE authoritative source covers STEMI criteria (ACC/AHA), "
                "but that single source is sufficient — alone ≠ weak."
            ),
            "target_state": "SUFFICIENT",
            "patient_case": PatientCase(
                case_id="demo_006_single_source",
                case_description="STEMI with single authoritative source — demonstrates alone ≠ weak",
                troponin=TroponinEvidence(
                    value=150.0,
                    unit="ng/L",
                    timestamp=datetime(2026, 9, 23, 9, 0, 0),
                    assay="Abbott Architect STAT High Sensitive Troponin-I",
                    serial_values=[
                        {"value": 8.0, "timestamp": "2026-09-23T06:00:00Z"},
                        {"value": 75.0, "timestamp": "2026-09-23T07:30:00Z"},
                    ],
                    extraction_confidence=0.99,
                    extraction_source="lab_report_006",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                ecg=ECGEvidence(
                    interpretation="ST elevation in leads V1-V4, consistent with anterior STEMI",
                    st_elevation=True,
                    st_depression=False,
                    q_waves=False,
                    timestamp=datetime(2026, 9, 23, 6, 15, 0),
                    quality="good",
                    extraction_confidence=0.99,
                    extraction_source="ecg_report_006",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                symptoms=SymptomsEvidence(
                    chest_pain=True,
                    onset_time=datetime(2026, 9, 23, 5, 30, 0),
                    characteristics="severe crushing substernal pain",
                    duration_minutes=210.0,
                    radiation="left arm",
                    associated_symptoms=["diaphoresis", "dyspnea", "nausea", "anxiety"],
                    extraction_confidence=0.98,
                    extraction_source="clinical_notes_006",
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                clinical_history=ClinicalHistory(
                    age=45,
                    sex="male",
                    diabetes=False,
                    hypertension=False,
                    smoking=True,
                    prior_mi=False,
                    family_history_cad=True,
                    extraction_confidence=0.97,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
                timing=TimingEvidence(
                    symptom_onset=datetime(2026, 9, 23, 5, 30, 0),
                    presentation_time=datetime(2026, 9, 23, 6, 0, 0),
                    onset_to_presentation_minutes=30.0,
                    serial_sample_spacing_minutes=180.0,
                    extraction_confidence=0.98,
                    verification_status=VerificationStatus.VERIFIED,
                    schema_valid=True,
                ),
            ),
        }
