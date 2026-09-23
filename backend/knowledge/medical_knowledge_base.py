"""
Curated medical knowledge base for AMI domain.

All thresholds trace to named, versioned sources.
No invented clinical thresholds. Every numeric cutoff references
a specific, sourced, versioned reference (§2.3, §5 of spec).
"""

from typing import List, Optional

from backend.schemas.medical_knowledge import (
    MedicalKnowledgeSource, StructuredClaim, AssayReference,
    SourceCondition, ClassOfRecommendation, LevelOfEvidence, EvidenceTier,
)
from backend.schemas.patient_evidence import PatientCase


class MedicalKnowledgeBase:
    """Curated, structured medical knowledge for AMI assessment.

    Sources:
      - Universal Definition of Myocardial Infarction (4th, 2018)
      - ACC/AHA/ACEP ACS Guideline (2021)
      - Older European guideline for conflict scenario
    Assay:
      - Abbott Architect STAT High Sensitive Troponin-I
    """

    def __init__(self):
        self._assay_references = self._build_assay_references()
        self._sources = self._build_sources()
        self._claims = self._build_claims()

    # ── Assay references ─────────────────────────────────────────────

    @staticmethod
    def _build_assay_references() -> List[AssayReference]:
        return [
            AssayReference(
                assay_name="Abbott Architect STAT High Sensitive Troponin-I",
                manufacturer="Abbott Diagnostics",
                unit="ng/L",
                sex_specific_limits={"male": 34.2, "female": 15.6},
                percentile_99_url=(
                    "https://www.corelaboratory.abbott/int/en/offerings/"
                    "segments/cardiac/architect-stat-high-sensitive-troponin-i"
                ),
                source_document="Abbott Architect STAT High Sensitive Troponin-I Package Insert",
                version_date="2023",
                provenance="Manufacturer package insert, referenced 99th percentile URL values",
            ),
        ]

    # ── Sources ──────────────────────────────────────────────────────

    @staticmethod
    def _build_sources() -> List[MedicalKnowledgeSource]:
        return [
            # Source 1: Universal Definition — myocardial injury
            MedicalKnowledgeSource(
                source_id="udmi_2018_injury",
                source_name="Fourth Universal Definition of Myocardial Infarction (2018)",
                version_date="2018",
                authority="ESC/ACC/AHA/WHF",
                class_of_recommendation=ClassOfRecommendation.CLASS_I,
                level_of_evidence=LevelOfEvidence.B_NR,
                evidence_tier=EvidenceTier.GUIDELINE,
                claim="myocardial_injury_criterion",
                condition=SourceCondition(
                    marker="cardiac_troponin",
                    comparison=">",
                    reference="assay_specific_99th_percentile_URL",
                    reference_value=None,
                    requires_serial=True,
                    serial_timeframe_hours=3.0,
                ),
                population="adult, suspected acute cardiac condition",
                scope="Definition of myocardial injury",
                provenance=(
                    "Thygesen K, et al. Fourth Universal Definition of "
                    "Myocardial Infarction (2018). Circulation. 2018;138(20):e231-e270."
                ),
                licensing_verified=False,
                applicable_context="acute_cardiac_assessment",
            ),

            # Source 2: Universal Definition — AMI Type 1
            MedicalKnowledgeSource(
                source_id="udmi_2018_ami_type1",
                source_name="Fourth Universal Definition of Myocardial Infarction (2018)",
                version_date="2018",
                authority="ESC/ACC/AHA/WHF",
                class_of_recommendation=ClassOfRecommendation.CLASS_I,
                level_of_evidence=LevelOfEvidence.B_NR,
                evidence_tier=EvidenceTier.GUIDELINE,
                claim="ami_type1_criterion",
                condition=SourceCondition(
                    marker="cardiac_troponin_plus_ischemia",
                    comparison="rise_and_fall",
                    reference="assay_specific_99th_percentile_URL_plus_clinical_ischemia",
                    reference_value=None,
                    requires_serial=True,
                    serial_timeframe_hours=3.0,
                ),
                population="adult, suspected ACS",
                scope="Diagnosis of acute myocardial infarction Type 1",
                provenance=(
                    "Thygesen K, et al. Fourth Universal Definition of "
                    "Myocardial Infarction (2018). Circulation. 2018;138(20):e231-e270."
                ),
                licensing_verified=False,
                applicable_context="acute_cardiac_assessment",
            ),

            # Source 3: ACC/AHA STEMI criteria
            MedicalKnowledgeSource(
                source_id="acc_aha_2021_stemi",
                source_name="2021 ACC/AHA/SCAI Guideline for Coronary Artery Revascularization",
                version_date="2021",
                authority="ACC/AHA/SCAI",
                class_of_recommendation=ClassOfRecommendation.CLASS_I,
                level_of_evidence=LevelOfEvidence.B_R,
                evidence_tier=EvidenceTier.GUIDELINE,
                claim="stemi_criteria",
                condition=SourceCondition(
                    marker="st_elevation",
                    comparison=">=",
                    reference="st_elevation_in_2_or_more_contiguous_leads",
                    reference_value=None,
                    requires_serial=False,
                ),
                population="adult, suspected STEMI",
                scope="STEMI identification for emergent reperfusion",
                provenance=(
                    "Lawton JS, et al. 2021 ACC/AHA/SCAI Guideline for "
                    "Coronary Artery Revascularization. Circulation. 2022;145(3):e18-e114."
                ),
                licensing_verified=False,
                applicable_context="acute_cardiac_assessment",
            ),

            # Source 4: ESC 0h/1h algorithm (for conflict scenario)
            MedicalKnowledgeSource(
                source_id="esc_2020_01h",
                source_name="2020 ESC Guidelines for NSTE-ACS (0h/1h Algorithm)",
                version_date="2020",
                authority="ESC",
                class_of_recommendation=ClassOfRecommendation.CLASS_I,
                level_of_evidence=LevelOfEvidence.B_NR,
                evidence_tier=EvidenceTier.GUIDELINE,
                claim="serial_troponin_protocol",
                condition=SourceCondition(
                    marker="cardiac_troponin",
                    comparison=">=",
                    reference="assay_specific_rule_in_cutoff",
                    reference_value=None,
                    requires_serial=True,
                    serial_timeframe_hours=1.0,
                ),
                population="adult, suspected NSTE-ACS",
                scope="Rapid rule-in/rule-out using 0h/1h hs-cTn algorithm",
                provenance=(
                    "Collet JP, et al. 2020 ESC Guidelines for the management "
                    "of acute coronary syndromes in patients presenting without "
                    "persistent ST-segment elevation. Eur Heart J. 2021;42(14):1289-1367."
                ),
                licensing_verified=False,
                applicable_context="acute_cardiac_assessment",
            ),

            # Source 5: Older guideline for conflict (different serial timing)
            MedicalKnowledgeSource(
                source_id="esc_2015_nsteacs",
                source_name="2015 ESC Guidelines for NSTE-ACS (Older, 0h/3h Algorithm)",
                version_date="2015",
                authority="ESC",
                class_of_recommendation=ClassOfRecommendation.CLASS_I,
                level_of_evidence=LevelOfEvidence.B_NR,
                evidence_tier=EvidenceTier.GUIDELINE,
                claim="serial_troponin_protocol",
                condition=SourceCondition(
                    marker="cardiac_troponin",
                    comparison="rise_and_fall",
                    reference="assay_specific_99th_percentile_URL_with_20pct_delta",
                    reference_value=None,
                    requires_serial=True,
                    serial_timeframe_hours=3.0,
                ),
                population="adult, suspected NSTE-ACS",
                scope="Serial troponin assessment using 0h/3h algorithm",
                provenance=(
                    "Roffi M, et al. 2015 ESC Guidelines for the management "
                    "of acute coronary syndromes in patients presenting without "
                    "persistent ST-segment elevation. Eur Heart J. 2016;37(3):267-315."
                ),
                licensing_verified=False,
                applicable_context="acute_cardiac_assessment",
            ),
        ]

    # ── Structured claims ────────────────────────────────────────────

    @staticmethod
    def _build_claims() -> List[StructuredClaim]:
        return [
            StructuredClaim(
                claim_id="myocardial_injury",
                claim_type="myocardial_injury",
                description="Cardiac troponin above 99th percentile URL with rise and/or fall pattern",
                conditions=[
                    SourceCondition(
                        marker="cardiac_troponin",
                        comparison=">",
                        reference="assay_specific_99th_percentile_URL",
                        requires_serial=True,
                        serial_timeframe_hours=3.0,
                    ),
                ],
                supporting_sources=["udmi_2018_injury"],
                population="adult, suspected acute cardiac condition",
                required_evidence=["troponin", "timing"],
                claim_text=(
                    "Myocardial injury is defined as detection of elevated cardiac "
                    "troponin values above the 99th percentile upper reference limit (URL) "
                    "with at least one value rising and/or falling."
                ),
            ),

            StructuredClaim(
                claim_id="ami_type1",
                claim_type="ami_diagnosis",
                description="Acute MI Type 1: myocardial injury plus clinical evidence of acute ischemia",
                conditions=[
                    SourceCondition(
                        marker="cardiac_troponin",
                        comparison=">",
                        reference="assay_specific_99th_percentile_URL",
                        requires_serial=True,
                        serial_timeframe_hours=3.0,
                    ),
                    SourceCondition(
                        marker="clinical_ischemia",
                        comparison="==",
                        reference="at_least_one_of_symptoms_ecg_imaging_angio",
                    ),
                ],
                supporting_sources=["udmi_2018_ami_type1"],
                population="adult, suspected ACS",
                required_evidence=["troponin", "timing", "symptoms", "ecg"],
                claim_text=(
                    "Type 1 AMI requires detection of rise and/or fall of cardiac "
                    "troponin with at least one value above the 99th percentile URL, "
                    "AND at least one of: symptoms of acute myocardial ischemia, "
                    "new ischemic ECG changes, development of pathological Q waves, "
                    "imaging evidence of new loss of viable myocardium or new regional "
                    "wall motion abnormality, or identification of coronary thrombus."
                ),
            ),

            StructuredClaim(
                claim_id="stemi_criteria",
                claim_type="stemi_criteria",
                description="STEMI: ST elevation in 2+ contiguous leads",
                conditions=[
                    SourceCondition(
                        marker="st_elevation",
                        comparison=">=",
                        reference="st_elevation_in_2_or_more_contiguous_leads",
                    ),
                ],
                supporting_sources=["acc_aha_2021_stemi"],
                population="adult, suspected STEMI",
                required_evidence=["ecg"],
                claim_text=(
                    "STEMI is identified by new ST-elevation at the J point in "
                    "two or more contiguous leads."
                ),
            ),

            StructuredClaim(
                claim_id="nstemi_criteria",
                claim_type="nstemi_criteria",
                description="NSTEMI: myocardial injury plus ischemia without persistent ST elevation",
                conditions=[
                    SourceCondition(
                        marker="cardiac_troponin",
                        comparison=">",
                        reference="assay_specific_99th_percentile_URL",
                        requires_serial=True,
                        serial_timeframe_hours=3.0,
                    ),
                    SourceCondition(
                        marker="clinical_ischemia_without_st_elevation",
                        comparison="==",
                        reference="ischemia_without_persistent_st_elevation",
                    ),
                ],
                supporting_sources=["udmi_2018_ami_type1"],
                population="adult, suspected NSTE-ACS",
                required_evidence=["troponin", "ecg", "symptoms", "timing"],
                claim_text=(
                    "NSTEMI is diagnosed when there is evidence of myocardial injury "
                    "(troponin rise/fall above 99th percentile URL) with clinical "
                    "evidence of ischemia, but WITHOUT persistent ST-segment elevation."
                ),
            ),

            StructuredClaim(
                claim_id="rapid_rule_in",
                claim_type="rapid_rule_in",
                description="Rapid rule-in / serial troponin testing protocol",
                conditions=[
                    SourceCondition(
                        marker="cardiac_troponin",
                        comparison=">=",
                        reference="assay_specific_rule_in_cutoff",
                        requires_serial=True,
                        serial_timeframe_hours=1.0,
                    ),
                ],
                supporting_sources=["esc_2020_01h", "esc_2015_nsteacs"],
                population="adult, suspected NSTE-ACS",
                required_evidence=["troponin", "timing"],
                claim_text=(
                    "Serial troponin timing algorithm for rapid assessment."
                ),
            ),
        ]

    # ── Public API ───────────────────────────────────────────────────

    def get_all_sources(self) -> List[MedicalKnowledgeSource]:
        return list(self._sources)

    def get_source(self, source_id: str) -> Optional[MedicalKnowledgeSource]:
        for s in self._sources:
            if s.source_id == source_id:
                return s
        return None

    def get_all_claims(self) -> List[StructuredClaim]:
        return list(self._claims)

    def get_claims_for_type(self, claim_type: str) -> List[StructuredClaim]:
        return [c for c in self._claims if c.claim_type == claim_type]

    def get_assay_reference(self, assay_name: str) -> Optional[AssayReference]:
        for a in self._assay_references:
            if a.assay_name.lower() == assay_name.lower():
                return a
        return None

    def get_default_assay(self) -> AssayReference:
        return self._assay_references[0]

    def get_applicable_claims(self, patient_case: PatientCase) -> List[StructuredClaim]:
        """Return claims relevant to the evidence present in this case."""
        present_evidence = set()

        if patient_case.troponin and patient_case.troponin.value is not None:
            present_evidence.add("troponin")
        if patient_case.ecg and patient_case.ecg.interpretation is not None:
            present_evidence.add("ecg")
        if patient_case.symptoms and patient_case.symptoms.chest_pain is not None:
            present_evidence.add("symptoms")
        if patient_case.imaging and patient_case.imaging.finding is not None:
            present_evidence.add("imaging")
        if patient_case.timing:
            present_evidence.add("timing")
        if patient_case.clinical_history:
            present_evidence.add("clinical_history")
        if patient_case.lab_context:
            present_evidence.add("lab_context")

        applicable = []
        for claim in self._claims:
            # A claim is applicable if ANY of its required evidence types
            # are present in the patient case
            required = set(claim.required_evidence)
            if required.intersection(present_evidence):
                # The rapid serial algorithm claim is specifically for 1h rapid protocols.
                # Only applicable when rapid serial sample spacing (<= 90 mins) is actually present.
                if claim.claim_id == "rapid_rule_in":
                    spacing = patient_case.timing.serial_sample_spacing_minutes if patient_case.timing else None
                    if not (spacing is not None and spacing <= 90):
                        continue
                applicable.append(claim)

        return applicable

    def get_sources_for_claims(self, claims: List[StructuredClaim]) -> List[MedicalKnowledgeSource]:
        """Get all sources that support the given claims."""
        source_ids = set()
        for claim in claims:
            source_ids.update(claim.supporting_sources)

        return [s for s in self._sources if s.source_id in source_ids]
