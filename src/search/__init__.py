"""Search orchestrator — public `search()` function.

Provider imports are deferred to call time so this package can be
imported by providers (for DTOs/enums) without circular import errors.
"""

from __future__ import annotations

from typing import List, Optional

from search.dto import SearchOptions, SearchPage, SearchResult
from search.enums import ProviderMode
from search.ranking import dedupe_results, expand_region_queries, score_result
from utils.logger import setup_logger

logger = setup_logger("search")

__all__ = ["search", "SearchOptions", "SearchPage", "SearchResult"]


def search(
    query: str,
    page: int = 1,
    limit: int = 20,
    options: Optional[SearchOptions] = None,
) -> SearchPage:
    """Search torrents and return one page of relevance-sorted results.

    When `provider_mode=MULTI` is requested but the vendored providers
    return nothing, we transparently fall back to the stable APIs so the
    user always sees results.
    """
    from providers.torrent_api_py import available_sites, search_multi_site
    from providers.pirate_bay import search_pirate_bay
    from providers.yts import search_yts

    options = options or SearchOptions()
    query = (query or "").strip()
    if not query:
        return SearchPage(results=[], total=0, pages=0)

    page = max(1, page)

    if options.provider_mode is ProviderMode.MULTI and available_sites():
        results = search_multi_site(
            query=query,
            page=page,
            sites=options.sites,
            category=options.category,
            region=options.region,
            limit_per_site=options.limit_per_site,
        )
        if results:
            return _paginate(results, page, limit)
        logger.warning("Torrent-Api-py returned no usable rows; falling back to stable APIs")

    stable_results = _run_stable(query, options, limit, search_pirate_bay, search_yts)
    return _paginate(stable_results, page, limit)


def _run_stable(query, options, limit, search_pirate_bay, search_yts) -> List[SearchResult]:
    queries = expand_region_queries(query, options.region)
    per_query_limit = max(limit, 20)
    collected: List[SearchResult] = []

    for candidate in queries:
        collected.extend(search_pirate_bay(candidate, 1, per_query_limit))
    collected.extend(search_yts(query, per_query_limit))

    unique = dedupe_results(collected)
    unique.sort(key=lambda r: score_result(r, query, options.region), reverse=True)
    return unique


def _paginate(results: List[SearchResult], page: int, limit: int) -> SearchPage:
    total = len(results)
    pages = (total + limit - 1) // limit if total else 0
    start = (page - 1) * limit
    end = start + limit
    return SearchPage(results=results[start:end], total=total, pages=pages)
