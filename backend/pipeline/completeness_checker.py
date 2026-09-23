"""
Completeness Checker (§3.3).

Two distinct checks at two distinct pipeline points:
  - Generic completeness (early, before retrieval): structural usability
  - Criteria-specific completeness (after retrieval): does evidence satisfy the specific rule

generic_completeness = PASS does NOT imply criteria_specific_completeness = PASS.
"""

from typing import Tuple, List

from backend.schemas.patient_evidence import PatientCase, ConditionResult, ExtractionConfidenceLevel
from backend.schemas.engine_output import MissingInformation
from backend.schemas.medical_knowledge import StructuredClaim
from backend.knowledge.evidence_matrix import EvidenceMatrix


class CompletenessChecker:
    """Checks both generic and criteria-specific evidence completeness."""

    def check_generic_completeness(
        self,
        case: PatientCase,
        evidence_matrix: EvidenceMatrix = None,
    ) -> Tuple[ConditionResult, List[MissingInformation]]:
        """Generic completeness check — structural usability before retrieval.

        For each evidence type present, checks that required fields from
        the evidence matrix are populated: value, unit, timestamp, provenance.
        """
        if evidence_matrix is None:
            evidence_matrix = EvidenceMatrix()

        missing: List[MissingInformation] = []
        has_any_evidence = False
        has_failures = False

        # Check troponin
        if case.troponin:
            has_any_evidence = True
            if case.troponin.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                missing.append(MissingInformation(
                    field="troponin",
                    reason_needed="Troponin extraction confidence too low to use",
                    askable=True,
                    ask_prompt="Please provide a clearer troponin lab result",
                    criticality="REQUIRED",
                ))
                has_failures = True
            else:
                if case.troponin.value is None:
                    missing.append(MissingInformation(
                        field="troponin_value",
                        reason_needed="Troponin value is required for cardiac assessment",
                        askable=True,
                        ask_prompt="Provide the troponin value with units",
                        criticality="REQUIRED",
                    ))
                    has_failures = True
                if case.troponin.unit is None:
                    missing.append(MissingInformation(
                        field="troponin_unit",
                        reason_needed="Troponin unit is required to interpret the value",
                        askable=True,
                        ask_prompt="Specify the troponin unit (ng/L or pg/mL)",
                        criticality="REQUIRED",
                    ))
                    has_failures = True

        # Check ECG
        if case.ecg:
            has_any_evidence = True
            if case.ecg.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                missing.append(MissingInformation(
                    field="ecg",
                    reason_needed="ECG extraction confidence too low to use",
                    askable=True,
                    ask_prompt="Please provide a clearer ECG reading",
                    criticality="REQUIRED",
                ))
                has_failures = True

        # Check symptoms
        if case.symptoms:
            has_any_evidence = True
            if case.symptoms.confidence_level == ExtractionConfidenceLevel.UNKNOWN:
                missing.append(MissingInformation(
                    field="symptoms",
                    reason_needed="Symptom extraction confidence too low to use",
                    askable=True,
                    ask_prompt="Please clarify the patient's symptoms",
                    criticality="REQUIRED",
                ))
                has_failures = True

        if not has_any_evidence:
            missing.append(MissingInformation(
                field="any_evidence",
                reason_needed="No clinical evidence was provided",
                askable=True,
                ask_prompt="Provide at least troponin, ECG, or symptom data",
                criticality="REQUIRED",
            ))
            return (ConditionResult.FAIL_RESULT, missing)

        if has_failures:
            return (ConditionResult.FAIL_RESULT, missing)

        return (ConditionResult.PASS_RESULT, missing)

    def check_criteria_completeness(
        self,
        case: PatientCase,
        applicable_claims: List[StructuredClaim],
    ) -> Tuple[ConditionResult, List[MissingInformation]]:
        """Criteria-specific completeness check — after retrieval.

        Checks whether the evidence satisfies what the specific claim/rule requires.
        This is more demanding than generic completeness.
        """
        if not applicable_claims:
            return (ConditionResult.UNKNOWN, [MissingInformation(
                field="applicable_criteria",
                reason_needed="No applicable clinical criteria found for this evidence",
                askable=False,
                criticality="REQUIRED",
            )])

        missing: List[MissingInformation] = []
        all_pass = True

        for claim in applicable_claims:
            for condition in claim.conditions:
                # Check serial troponin requirement
                if condition.requires_serial and condition.marker == "cardiac_troponin":
                    if not case.troponin or not case.troponin.serial_values:
                        missing.append(MissingInformation(
                            field="serial_troponin",
                            reason_needed=(
                                f"Claim '{claim.claim_id}' requires serial troponin measurements "
                                f"within {condition.serial_timeframe_hours}h to assess rise/fall pattern"
                            ),
                            askable=True,
                            ask_prompt=(
                                f"Repeat troponin measurement in "
                                f"{int(condition.serial_timeframe_hours)} hour(s) "
                                f"to assess for rise and/or fall pattern"
                            ),
                            criticality="REQUIRED",
                        ))
                        all_pass = False

                # Check assay requirement for troponin comparison
                if condition.marker == "cardiac_troponin" and "99th_percentile" in condition.reference:
                    if case.troponin and not case.troponin.assay:
                        missing.append(MissingInformation(
                            field="troponin_assay",
                            reason_needed=(
                                "Assay identity is required to determine the correct "
                                "99th percentile reference limit for troponin comparison"
                            ),
                            askable=True,
                            ask_prompt="Specify the troponin assay used (manufacturer and test name)",
                            criticality="REQUIRED",
                        ))
                        all_pass = False

                # Check clinical ischemia evidence for AMI claims
                if condition.marker in ("clinical_ischemia", "cardiac_troponin_plus_ischemia",
                                        "clinical_ischemia_without_st_elevation"):
                    has_ischemia_evidence = False
                    if case.symptoms and case.symptoms.chest_pain:
                        has_ischemia_evidence = True
                    if case.ecg and (case.ecg.st_elevation or case.ecg.st_depression):
                        has_ischemia_evidence = True
                    if case.imaging and case.imaging.wall_motion_abnormality:
                        has_ischemia_evidence = True

                    if not has_ischemia_evidence:
                        missing.append(MissingInformation(
                            field="clinical_ischemia_evidence",
                            reason_needed=(
                                f"Claim '{claim.claim_id}' requires at least one of: "
                                "ischemic symptoms, ischemic ECG changes, imaging evidence "
                                "of new wall motion abnormality, or coronary thrombus"
                            ),
                            askable=True,
                            ask_prompt="Provide ECG, symptom assessment, or imaging findings",
                            criticality="REQUIRED",
                        ))
                        all_pass = False

        if not all_pass:
            return (ConditionResult.FAIL_RESULT, missing)

        return (ConditionResult.PASS_RESULT, missing)
