"""
Claim Registry — loads structured claim data from JSON files.

Adding a new disease domain = adding a new JSON file under
backend/knowledge/data/. Zero engine code changes needed.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.schemas.medical_knowledge import (
    StructuredClaim, MedicalKnowledgeSource, AssayReference,
    SourceCondition, ConditionNode,
    ClassOfRecommendation, LevelOfEvidence, EvidenceTier,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"


def _parse_condition_node(d: dict) -> ConditionNode:
    """Recursively parse a dict into a ConditionNode tree."""
    children = None
    if d.get("children"):
        children = [_parse_condition_node(c) for c in d["children"]]
    return ConditionNode(
        type=d["type"],
        children=children,
        check=d.get("check"),
        evidence_type=d.get("evidence_type"),
        field=d.get("field"),
        params=d.get("params"),
    )


def _safe_enum(enum_cls, value):
    """Convert a string to an enum value, or None if not valid."""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return None


class ClaimRegistry:
    """Registry of validated clinical claims loaded from JSON data files.

    Scans backend/knowledge/data/ for *.json files on init.
    """

    def __init__(self):
        self._claims: Dict[str, StructuredClaim] = {}
        self._sources: Dict[str, MedicalKnowledgeSource] = {}
        self._assay_refs: Dict[str, AssayReference] = {}
        self._domains: List[str] = []
        self._claim_to_sources: Dict[str, List[str]] = {}
        self._load_all()

    def _load_all(self):
        if not _DATA_DIR.exists():
            logger.warning(f"Knowledge data directory not found: {_DATA_DIR}")
            return
        for path in sorted(_DATA_DIR.glob("*.json")):
            try:
                self._load_file(path)
            except Exception as e:
                logger.error(f"Failed to load knowledge file {path}: {e}")

    def _load_file(self, path: Path):
        with open(path, "r") as f:
            data = json.load(f)

        domain = data.get("domain", path.stem)
        self._domains.append(domain)
        logger.info(f"Loading knowledge domain: {domain} from {path.name}")

        # Assay references
        for ar in data.get("assay_references", []):
            ref = AssayReference(
                assay_name=ar["assay_name"],
                manufacturer=ar["manufacturer"],
                unit=ar["unit"],
                sex_specific_limits=ar["sex_specific_limits"],
                percentile_99_url=ar.get("percentile_99_url"),
                source_document=ar["source_document"],
                version_date=ar.get("version_date"),
                provenance=ar["provenance"],
            )
            self._assay_refs[ref.assay_name] = ref

        # Sources
        for src in data.get("sources", []):
            cond = src["condition"]
            source = MedicalKnowledgeSource(
                source_id=src["source_id"],
                source_name=src["source_name"],
                version_date=src.get("version_date"),
                authority=src["authority"],
                class_of_recommendation=_safe_enum(ClassOfRecommendation, src.get("class_of_recommendation")),
                level_of_evidence=_safe_enum(LevelOfEvidence, src.get("level_of_evidence")),
                evidence_tier=_safe_enum(EvidenceTier, src.get("evidence_tier")),
                claim=src["claim"],
                condition=SourceCondition(
                    marker=cond["marker"],
                    comparison=cond["comparison"],
                    reference=cond["reference"],
                    reference_value=cond.get("reference_value"),
                    requires_serial=cond.get("requires_serial", False),
                    serial_timeframe_hours=cond.get("serial_timeframe_hours"),
                ),
                population=src["population"],
                scope=src.get("scope"),
                provenance=src["provenance"],
                licensing_verified=src.get("licensing_verified", False),
                applicable_context=src.get("applicable_context"),
            )
            self._sources[source.source_id] = source

        # Claims
        for cl in data.get("claims", []):
            conditions = [
                SourceCondition(
                    marker=c["marker"],
                    comparison=c["comparison"],
                    reference=c["reference"],
                    reference_value=c.get("reference_value"),
                    requires_serial=c.get("requires_serial", False),
                    serial_timeframe_hours=c.get("serial_timeframe_hours"),
                )
                for c in cl.get("conditions", [])
            ]
            condition_tree = None
            if cl.get("condition_tree"):
                condition_tree = _parse_condition_node(cl["condition_tree"])

            claim = StructuredClaim(
                claim_id=cl["claim_id"],
                claim_type=cl["claim_type"],
                description=cl["description"],
                conditions=conditions,
                supporting_sources=cl.get("supporting_sources", []),
                population=cl.get("population", ""),
                required_evidence=cl.get("required_evidence", []),
                claim_text=cl.get("claim_text", ""),
                condition_tree=condition_tree,
                strength_rank=cl.get("strength_rank", 1),
                what_this_supports=cl.get("what_this_supports"),
                what_this_cannot_establish=cl.get("what_this_cannot_establish"),
            )
            self._claims[claim.claim_id] = claim
            self._claim_to_sources[claim.claim_id] = cl.get("supporting_sources", [])

    # ── Public API ───────────────────────────────────────────────────

    def get_claim(self, claim_id: str) -> Optional[StructuredClaim]:
        return self._claims.get(claim_id)

    def get_all_claims(self) -> List[StructuredClaim]:
        return list(self._claims.values())

    def get_all_claim_ids(self) -> List[str]:
        return list(self._claims.keys())

    def claim_exists(self, claim_id: str) -> bool:
        return claim_id in self._claims

    def get_sources_for_claim(self, claim_id: str) -> List[MedicalKnowledgeSource]:
        source_ids = self._claim_to_sources.get(claim_id, [])
        return [self._sources[sid] for sid in source_ids if sid in self._sources]

    def get_assay_reference(self, assay_name: str) -> Optional[AssayReference]:
        """Look up assay reference by exact name match."""
        return self._assay_refs.get(assay_name)

    def get_assay_reference_fuzzy(self, assay_name: str) -> Optional[AssayReference]:
        """Look up assay reference by substring match."""
        if not assay_name:
            return None
        assay_lower = assay_name.lower()
        for name, ref in self._assay_refs.items():
            if name.lower() in assay_lower or assay_lower in name.lower():
                return ref
        return None

    def get_available_domains(self) -> List[str]:
        return list(self._domains)

    def get_claim_descriptions(self) -> Dict[str, str]:
        return {cid: c.description for cid, c in self._claims.items()}
