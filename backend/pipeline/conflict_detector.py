"""
Conflict Detector (§3.5) — Source comparison / conflict detection.

Conflict requires two or more applicable sources.
Never resolve by majority vote. Report conflicts, don't pretend to resolve them.
A single authoritative source can still independently support SUFFICIENT.
"""

from typing import Tuple, List

from backend.schemas.patient_evidence import ConflictStatus, CorroborationStatus
from backend.schemas.medical_knowledge import MedicalKnowledgeSource, SourceAssessment
from backend.schemas.engine_output import ConflictDetail


class ConflictDetector:
    """Detects material conflicts between applicable sources.

    Conflict means: both sources address the same claim, both are applicable
    to this patient/context, and their structured conditions materially
    disagree in a way that affects the conclusion.

    Never resolve by majority vote — a repeated low-authority source does
    not outweigh one current authoritative guideline.
    """

    def detect_conflicts(
        self,
        sources: List[MedicalKnowledgeSource],
        assessments: List[SourceAssessment],
    ) -> Tuple[ConflictStatus, CorroborationStatus, List[ConflictDetail]]:
        """Detect conflicts among applicable sources.

        Args:
            sources: All retrieved medical knowledge sources.
            assessments: Per-source assessments from SourceAssessor.

        Returns:
            (conflict_status, corroboration_status, conflict_details)
        """
        # Filter to applicable sources
        applicable_source_ids = {
            a.source_id for a in assessments
            if a.applicability in ("APPLICABLE", "PARTIALLY_APPLICABLE")
            and a.relevance in ("DIRECTLY_RELEVANT", "PARTIALLY_RELEVANT")
        }
        applicable_sources = [s for s in sources if s.source_id in applicable_source_ids]

        # Per §3.5: handle 0, 1, and 2+ source scenarios
        if len(applicable_sources) == 0:
            return (
                ConflictStatus.NOT_ASSESSABLE,
                CorroborationStatus.NOT_ASSESSABLE,
                [],
            )

        if len(applicable_sources) == 1:
            # A single authoritative source can still independently support SUFFICIENT.
            # "No conflict" ≠ "sources agree"
            return (
                ConflictStatus.NOT_ASSESSABLE,
                CorroborationStatus.NOT_ASSESSABLE,
                [],
            )

        # 2+ applicable sources → compare structured claims
        conflicts: List[ConflictDetail] = []
        corroborated = True

        # Group sources by claim
        claim_groups: dict[str, List[MedicalKnowledgeSource]] = {}
        for source in applicable_sources:
            claim_groups.setdefault(source.claim, []).append(source)

        # Check for conflicts within each claim group
        for claim, claim_sources in claim_groups.items():
            if len(claim_sources) < 2:
                continue

            # Compare each pair
            for i in range(len(claim_sources)):
                for j in range(i + 1, len(claim_sources)):
                    src_a = claim_sources[i]
                    src_b = claim_sources[j]

                    conflict = self._compare_conditions(src_a, src_b, claim)
                    if conflict:
                        conflicts.append(conflict)
                        corroborated = False

        # Also check for conflicts between sources addressing related claims
        # (e.g., different algorithms for the same clinical question)
        related_claim_groups = self._find_related_claims(claim_groups)
        for claim_a, claim_b, sources_a, sources_b in related_claim_groups:
            for src_a in sources_a:
                for src_b in sources_b:
                    conflict = self._compare_related_conditions(
                        src_a, src_b, claim_a, claim_b
                    )
                    if conflict:
                        conflicts.append(conflict)
                        corroborated = False

        if conflicts:
            return (
                ConflictStatus.CONFLICT,
                CorroborationStatus.NOT_CORROBORATED,
                conflicts,
            )

        return (
            ConflictStatus.NO_CONFLICT,
            CorroborationStatus.CORROBORATED if corroborated else CorroborationStatus.NOT_CORROBORATED,
            [],
        )

    def _compare_conditions(
        self,
        src_a: MedicalKnowledgeSource,
        src_b: MedicalKnowledgeSource,
        claim: str,
    ) -> ConflictDetail | None:
        """Compare two sources addressing the same claim for material disagreement."""
        cond_a = src_a.condition
        cond_b = src_b.condition

        disagreements = []

        # Check comparison operator
        if cond_a.comparison != cond_b.comparison:
            disagreements.append(
                f"comparison method: '{cond_a.comparison}' vs '{cond_b.comparison}'"
            )

        # Check reference values
        if (cond_a.reference_value is not None and cond_b.reference_value is not None
                and cond_a.reference_value != cond_b.reference_value):
            disagreements.append(
                f"reference value: {cond_a.reference_value} vs {cond_b.reference_value}"
            )

        # Check serial requirements
        if cond_a.requires_serial != cond_b.requires_serial:
            disagreements.append(
                f"serial requirement: {cond_a.requires_serial} vs {cond_b.requires_serial}"
            )

        # Check serial timeframe
        if (cond_a.serial_timeframe_hours is not None
                and cond_b.serial_timeframe_hours is not None
                and cond_a.serial_timeframe_hours != cond_b.serial_timeframe_hours):
            disagreements.append(
                f"serial timeframe: {cond_a.serial_timeframe_hours}h vs {cond_b.serial_timeframe_hours}h"
            )

        # Check reference methodology
        if cond_a.reference != cond_b.reference:
            disagreements.append(
                f"reference method: '{cond_a.reference}' vs '{cond_b.reference}'"
            )

        if not disagreements:
            return None

        return ConflictDetail(
            claim=claim,
            source_a=src_a.source_id,
            source_a_position=(
                f"{src_a.source_name}: {cond_a.marker} {cond_a.comparison} "
                f"{cond_a.reference}"
                + (f" (serial: {cond_a.serial_timeframe_hours}h)" if cond_a.requires_serial else "")
            ),
            source_b=src_b.source_id,
            source_b_position=(
                f"{src_b.source_name}: {cond_b.marker} {cond_b.comparison} "
                f"{cond_b.reference}"
                + (f" (serial: {cond_b.serial_timeframe_hours}h)" if cond_b.requires_serial else "")
            ),
            resolution_possible=False,
            resolution_note=(
                "Material disagreement detected: " + "; ".join(disagreements) +
                ". This conflict is reported, not resolved — the system does not pick a side."
            ),
        )

    def _find_related_claims(
        self,
        claim_groups: dict,
    ) -> list:
        """Find pairs of claim groups that address related clinical questions."""
        related_pairs = []

        # Define claim relationships
        related_claim_types = {
            ("rapid_rule_in_criterion", "serial_troponin_criterion"),
        }

        claims = list(claim_groups.keys())
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                if (claims[i], claims[j]) in related_claim_types or \
                   (claims[j], claims[i]) in related_claim_types:
                    related_pairs.append((
                        claims[i], claims[j],
                        claim_groups[claims[i]], claim_groups[claims[j]],
                    ))

        return related_pairs

    def _compare_related_conditions(
        self,
        src_a: MedicalKnowledgeSource,
        src_b: MedicalKnowledgeSource,
        claim_a: str,
        claim_b: str,
    ) -> ConflictDetail | None:
        """Compare sources from related claims for material disagreement."""
        cond_a = src_a.condition
        cond_b = src_b.condition

        # Only flag as conflict if they address the same marker with different requirements
        if cond_a.marker != cond_b.marker:
            return None

        # Check for material disagreement in serial timing
        if (cond_a.requires_serial and cond_b.requires_serial
                and cond_a.serial_timeframe_hours is not None
                and cond_b.serial_timeframe_hours is not None
                and cond_a.serial_timeframe_hours != cond_b.serial_timeframe_hours):
            return ConflictDetail(
                claim=f"{claim_a} vs {claim_b}",
                source_a=src_a.source_id,
                source_a_position=(
                    f"{src_a.source_name}: requires serial within "
                    f"{cond_a.serial_timeframe_hours}h using {cond_a.reference}"
                ),
                source_b=src_b.source_id,
                source_b_position=(
                    f"{src_b.source_name}: requires serial within "
                    f"{cond_b.serial_timeframe_hours}h using {cond_b.reference}"
                ),
                resolution_possible=False,
                resolution_note=(
                    "Sources use different serial timing algorithms. "
                    "This system does not resolve by majority vote."
                ),
            )

        return None
