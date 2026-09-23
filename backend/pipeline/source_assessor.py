"""
Source Assessor (§3.4) — Independent of any claim.

Computed once per retrieved source, reusable across queries.
Dimensions are kept SEPARATE, never collapsed into one confidence percentage.
"""

from typing import List
from datetime import datetime

from backend.schemas.medical_knowledge import (
    MedicalKnowledgeSource, SourceAssessment,
    ClassOfRecommendation, LevelOfEvidence, EvidenceTier,
)
from backend.schemas.patient_evidence import PatientCase


# Domain-appropriate staleness thresholds (years)
CURRENT_THRESHOLD = 3
AGING_THRESHOLD = 5


class SourceAssessor:
    """Per-source assessment independent of any claim.

    Dimensions kept separate:
      - Source reliability: can this one source be trusted
      - Evidence quality: is this evidence usable for this question
      - Relevance: does it address the claim at all
      - Applicability: does the rule apply to this patient/context
      - Consistency: does it agree with other evidence (set after comparison)
    """

    def assess_source(
        self,
        source: MedicalKnowledgeSource,
        patient_case: PatientCase,
    ) -> SourceAssessment:
        """Assess a single source on all dimensions."""
        return SourceAssessment(
            source_id=source.source_id,
            reliability=self._assess_reliability(source),
            evidence_quality=self._assess_evidence_quality(source),
            relevance=self._assess_relevance(source, patient_case),
            applicability=self._assess_applicability(source, patient_case),
            recency_status=self._assess_recency(source),
            population_match=self._assess_population_match(source, patient_case),
            staleness_years=self._compute_staleness(source),
            notes=None,
        )

    def assess_all_sources(
        self,
        sources: List[MedicalKnowledgeSource],
        patient_case: PatientCase,
    ) -> List[SourceAssessment]:
        """Assess all sources independently."""
        return [self.assess_source(s, patient_case) for s in sources]

    # ── Private assessment methods ───────────────────────────────────

    def _assess_reliability(self, source: MedicalKnowledgeSource) -> str:
        """Reliability based on evidence tier and class of recommendation."""
        # Class of recommendation takes precedence if available
        if source.class_of_recommendation:
            if source.class_of_recommendation in (
                ClassOfRecommendation.CLASS_I,
            ):
                return "HIGH"
            elif source.class_of_recommendation == ClassOfRecommendation.CLASS_IIA:
                return "MODERATE"
            elif source.class_of_recommendation == ClassOfRecommendation.CLASS_IIB:
                return "LOW"
            elif source.class_of_recommendation == ClassOfRecommendation.CLASS_III:
                return "LOW"

        # Fall back to evidence tier
        if source.evidence_tier:
            tier_map = {
                EvidenceTier.RCT: "HIGH",
                EvidenceTier.GUIDELINE: "HIGH",
                EvidenceTier.COHORT: "MODERATE",
                EvidenceTier.CASE_REPORT: "LOW",
                EvidenceTier.EXPERT_OPINION: "LOW",
            }
            return tier_map.get(source.evidence_tier, "UNKNOWN")

        return "UNKNOWN"

    def _assess_evidence_quality(self, source: MedicalKnowledgeSource) -> str:
        """Quality based on level of evidence."""
        if source.level_of_evidence:
            loe_map = {
                LevelOfEvidence.A: "HIGH",
                LevelOfEvidence.B_R: "HIGH",
                LevelOfEvidence.B_NR: "MODERATE",
                LevelOfEvidence.C_LD: "LOW",
                LevelOfEvidence.C_EO: "LOW",
            }
            return loe_map.get(source.level_of_evidence, "UNKNOWN")

        # Derive from tier if no level of evidence
        if source.evidence_tier:
            tier_map = {
                EvidenceTier.RCT: "HIGH",
                EvidenceTier.GUIDELINE: "MODERATE",
                EvidenceTier.COHORT: "MODERATE",
                EvidenceTier.CASE_REPORT: "LOW",
                EvidenceTier.EXPERT_OPINION: "LOW",
            }
            return tier_map.get(source.evidence_tier, "UNKNOWN")

        return "UNKNOWN"

    def _assess_relevance(
        self,
        source: MedicalKnowledgeSource,
        patient_case: PatientCase,
    ) -> str:
        """Does the source address a claim relevant to this case?"""
        # Check if the source's claim relates to available evidence
        relevant_markers = set()
        if patient_case.troponin:
            relevant_markers.update(["cardiac_troponin", "cardiac_troponin_plus_ischemia"])
        if patient_case.ecg:
            relevant_markers.add("st_elevation")
        if patient_case.symptoms:
            relevant_markers.update(["clinical_ischemia", "clinical_ischemia_without_st_elevation"])

        if source.condition.marker in relevant_markers:
            return "DIRECTLY_RELEVANT"

        # Check if the source is in the cardiac domain at all
        cardiac_keywords = ["troponin", "cardiac", "ischemia", "mi", "acs", "stemi", "nstemi", "st_elevation"]
        if any(kw in source.condition.marker.lower() for kw in cardiac_keywords):
            return "PARTIALLY_RELEVANT"

        return "NOT_RELEVANT"

    def _assess_applicability(
        self,
        source: MedicalKnowledgeSource,
        patient_case: PatientCase,
    ) -> str:
        """Does the rule apply to this patient/context?"""
        population_lower = source.population.lower()

        # Check adult population match
        if "adult" in population_lower:
            if patient_case.clinical_history and patient_case.clinical_history.age:
                if patient_case.clinical_history.age < 18:
                    return "NOT_APPLICABLE"

        # Check if ACS-specific source matches an ACS-suspected case
        if "acs" in population_lower or "acute coronary" in population_lower:
            has_acs_evidence = (
                (patient_case.troponin and patient_case.troponin.value is not None) or
                (patient_case.ecg and patient_case.ecg.interpretation is not None) or
                (patient_case.symptoms and patient_case.symptoms.chest_pain)
            )
            if has_acs_evidence:
                return "APPLICABLE"
            return "PARTIALLY_APPLICABLE"

        # Check STEMI-specific sources
        if "stemi" in population_lower:
            if patient_case.ecg and case_ecg_has_st_elevation(patient_case.ecg):
                return "APPLICABLE"
            return "PARTIALLY_APPLICABLE"

        return "APPLICABLE"

    def _assess_recency(self, source: MedicalKnowledgeSource) -> str:
        """Compare version_date against staleness thresholds."""
        staleness = self._compute_staleness(source)
        if staleness is None:
            return "UNKNOWN"
        if staleness <= CURRENT_THRESHOLD:
            return "CURRENT"
        elif staleness <= AGING_THRESHOLD:
            return "AGING"
        else:
            return "OUTDATED"

    def _assess_population_match(
        self,
        source: MedicalKnowledgeSource,
        patient_case: PatientCase,
    ) -> str:
        """Check if the source population matches the patient."""
        if not patient_case.clinical_history:
            return "UNKNOWN"

        population_lower = source.population.lower()

        # Age check
        if patient_case.clinical_history.age:
            if "adult" in population_lower and patient_case.clinical_history.age < 18:
                return "MISMATCH"
            if "pediatric" in population_lower and patient_case.clinical_history.age >= 18:
                return "MISMATCH"

        return "MATCHED"

    def _compute_staleness(self, source: MedicalKnowledgeSource) -> float | None:
        """Compute staleness in years from version_date."""
        if not source.version_date:
            return None
        try:
            year = int(source.version_date[:4])
            current_year = datetime.now().year
            return current_year - year
        except (ValueError, IndexError):
            return None


def case_ecg_has_st_elevation(ecg) -> bool:
    """Helper to check if ECG evidence shows ST elevation."""
    return ecg.st_elevation is True
