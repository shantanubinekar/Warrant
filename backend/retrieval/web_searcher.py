"""
Medical Web Searcher — Live web search restricted to trusted medical domains.
Uses duckduckgo-search (DDGS).
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.info("ddgs / duckduckgo-search not installed — live web search disabled")

TRUSTED_DOMAINS = [
    "escardio.org",
    "ahajournals.org",
    "nejm.org",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "acc.org",
    "heart.org",
    "who.int",
]


class MedicalWebSearcher:
    """Performs live web searches restricted to trusted medical domains."""

    def __init__(self, max_results_per_search: int = 3):
        self.max_results_per_search = max_results_per_search
        self.available = DDGS_AVAILABLE

    def search(self, query: str, domain: Optional[str] = None) -> List[Dict[str, str]]:
        """Perform a single domain-scoped search."""
        if not self.available:
            logger.warning("DDGS not available — search skipped")
            return []

        search_query = query
        if domain:
            search_query = f"site:{domain} {query}"

        results = []
        try:
            with DDGS(timeout=5) as ddgs:
                raw_results = list(ddgs.text(search_query, max_results=self.max_results_per_search))
                for item in raw_results:
                    url = item.get("href", "")
                    matched_domain = domain or self._extract_domain(url)
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "url": url,
                        "domain": matched_domain,
                    })
        except Exception as e:
            logger.warning(f"Web search error for '{search_query}': {e}")
            return []

        return results

    def search_trusted(self, query: str) -> List[Dict[str, str]]:
        """Search across all trusted domains by filtering results."""
        if not self.available:
            return []

        results = []
        try:
            with DDGS(timeout=5) as ddgs:
                raw_results = list(ddgs.text(query, max_results=self.max_results_per_search * 2))
                for item in raw_results:
                    url = item.get("href", "")
                    matched_domain = self._extract_domain(url)
                    if any(trusted in matched_domain for trusted in TRUSTED_DOMAINS):
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("body", ""),
                            "url": url,
                            "domain": matched_domain,
                        })
                        if len(results) >= self.max_results_per_search:
                            break
        except Exception as e:
            logger.warning(f"Trusted search error for '{query}': {e}")
            return []

        return results

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""
