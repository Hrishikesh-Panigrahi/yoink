"""Region-aware query expansion, deduping, and score functions."""

from __future__ import annotations

from typing import Iterable, List

from search.dto import SearchResult
from search.enums import Region, region_terms


def expand_region_queries(query: str, region: Region) -> List[str]:
    """Add region marker tokens (e.g. "hindi") to the base query when missing."""
    base = (query or "").strip()
    if not base:
        return []
    queries = [base]
    lowered = base.lower()
    for term in region_terms(region):
        if term not in lowered:
            queries.append(f"{base} {term}")
    return queries


def dedupe_results(results: Iterable[SearchResult]) -> List[SearchResult]:
    """Drop duplicates by magnet URL, falling back to title."""
    seen: set[str] = set()
    unique: List[SearchResult] = []
    for result in results:
        key = (result.magnet_url or result.title).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def score_result(result: SearchResult, query: str, region: Region) -> float:
    """Score a result against the query, biased by region markers + seeds."""
    title = result.title.lower()
    tokens = [tok for tok in query.lower().split() if tok]
    score = sum(100 for tok in tokens if tok in title)
    if query.lower() in title:
        score += 150

    haystack = " ".join(
        [
            result.title,
            result.source,
            result.language or "",
            " ".join(result.genres or []),
            result.summary or "",
        ]
    ).lower()
    score += sum(60 for term in region_terms(region) if term in haystack)
    score += min(result.seeds, 5000) / 50
    score += min(result.peers, 5000) / 100
    return score
