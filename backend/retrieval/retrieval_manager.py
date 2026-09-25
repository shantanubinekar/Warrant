"""
Requirement-Driven Retrieval Manager.

CRITICAL ARCHITECTURAL SAFETY:
Retrieved text is used EXCLUSIVELY for citations, grounding, and provenance traces.
Retrieved text is NEVER interpreted by the LLM into executable rules, clinical thresholds,
or diagnostic logic. The deterministic reasoning engine only evaluates against curated,
validated knowledge-data entries.
"""

import logging
from typing import List, Dict, Optional

from backend.retrieval.web_searcher import MedicalWebSearcher, TRUSTED_DOMAINS
from backend.schemas.medical_knowledge import StructuredClaim
from backend.schemas.engine_output import RetrievalCitation

logger = logging.getLogger(__name__)

MAX_TOTAL_SEARCHES = 6
MAX_ROUNDS_PER_REQUIREMENT = 2

DOMAIN_PREFERENCE: Dict[str, List[str]] = {
    "troponin": ["escardio.org", "ahajournals.org"],
    "ecg": ["ahajournals.org", "acc.org"],
    "ischemia": ["escardio.org", "ahajournals.org"],
    "symptoms": ["escardio.org", "ahajournals.org"],
    "stemi": ["acc.org", "ahajournals.org"],
    "nstemi": ["escardio.org", "ahajournals.org"],
    "timing": ["escardio.org", "ncbi.nlm.nih.gov"],
    "serial": ["escardio.org", "ncbi.nlm.nih.gov"],
    "imaging": ["escardio.org", "ahajournals.org"],
}


class RetrievalManager:
    """Manages requirement-driven web retrieval for evidence grounding."""

    def __init__(self, searcher: Optional[MedicalWebSearcher] = None):
        self.searcher = searcher or MedicalWebSearcher()
        self.search_count = 0

    def reset(self):
        """Reset search counter per request."""
        self.search_count = 0

    def retrieve_for_claim(self, claim: StructuredClaim) -> List[RetrievalCitation]:
        """Retrieve authoritative citations for each required evidence item in a claim.

        Hard cap: MAX_TOTAL_SEARCHES (6).
        Max 2 rounds per requirement.
        """
        citations: List[RetrievalCitation] = []
        if not self.searcher.available:
            return citations

        for requirement in claim.required_evidence:
            if self.search_count >= MAX_TOTAL_SEARCHES:
                logger.info(f"Retrieval hard cap of {MAX_TOTAL_SEARCHES} searches reached.")
                break

            preferred_domains = DOMAIN_PREFERENCE.get(requirement.lower(), ["ncbi.nlm.nih.gov"])
            primary_domain = preferred_domains[0]

            # Round 1: Targeted search
            query = f"{requirement} acute myocardial infarction criteria {claim.description}"
            results = self.searcher.search(query, domain=primary_domain)
            self.search_count += 1

            # Round 2: Broader reformulation if no results and under cap
            if not results and self.search_count < MAX_TOTAL_SEARCHES:
                broader_query = f"{requirement} guidelines myocardial infarction"
                results = self.searcher.search_trusted(broader_query)
                self.search_count += 1

            for res in results:
                snippet_lower = res.get("snippet", "").lower()
                relevance = "MODERATE"
                if requirement.lower() in snippet_lower or "infarction" in snippet_lower:
                    relevance = "HIGH"

                citations.append(
                    RetrievalCitation(
                        query=query,
                        domain=res.get("domain", primary_domain),
                        title=res.get("title", ""),
                        snippet=res.get("snippet", ""),
                        url=res.get("url"),
                        requirement_matched=requirement,
                        relevance=relevance,
                    )
                )

        return citations
