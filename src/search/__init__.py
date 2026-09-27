from __future__ import annotations

from typing import List, Optional

from search.dto import SearchOptions, SearchPage, SearchResult
from search.enums import ProviderMode
from search.ranking import (
    dedupe_results,
    expand_region_queries,
    filter_by_min_seeds,
    filter_by_quality,
    sort_results,
)
from utils.logger import setup_logger

logger = setup_logger("search")

__all__ = ["search", "SearchOptions", "SearchPage", "SearchResult"]


def search(
    query: str,
    page: int = 1,
    limit: int = 20,
    options: Optional[SearchOptions] = None,
) -> SearchPage:
    # Imported here because the providers import search.dto and search.enums.
    # A top-level import would be circular.
    from providers.pirate_bay import search_pirate_bay
    from providers.torrent_api_py import available_sites, search_multi_site

    options = options or SearchOptions()
    query = (query or "").strip()
    if not query:
        return SearchPage(results=[], total=0, pages=0)

    page = max(1, page)

    if options.provider_mode is ProviderMode.MULTI and available_sites():
        raw = search_multi_site(
            query=query,
            page=page,
            sites=options.sites,
            category=options.category,
            region=options.region,
            limit_per_site=options.limit_per_site,
        )
        if options.include_stable:
            raw = raw + _run_stable(query, options, limit, search_pirate_bay)
        if raw:
            return _finalize(raw, query, options, page, limit)
        logger.warning("Torrent-Api-py returned no usable rows; falling back to stable APIs")

    stable_raw = _run_stable(query, options, limit, search_pirate_bay)
    return _finalize(stable_raw, query, options, page, limit)


def _run_stable(query, options, limit, search_pirate_bay) -> List[SearchResult]:
    enabled = options.enabled_stable
    if enabled is not None and "piratebay_stable" not in enabled:
        return []
    per_query_limit = max(limit, 20)
    collected: List[SearchResult] = []
    for candidate in expand_region_queries(query, options.region):
        collected.extend(
            search_pirate_bay(candidate, 1, per_query_limit, category=options.category)
        )
    return collected


def _finalize(
    raw: List[SearchResult],
    query: str,
    options: SearchOptions,
    page: int,
    limit: int,
) -> SearchPage:
    unique = dedupe_results(raw)
    unique = filter_by_quality(unique, options.quality)
    unique = filter_by_min_seeds(unique, options.min_seeds)
    ordered = sort_results(unique, options.sort_by, query, options.region)
    return _paginate(ordered, page, limit)


def _paginate(results: List[SearchResult], page: int, limit: int) -> SearchPage:
    total = len(results)
    pages = (total + limit - 1) // limit if total else 0
    start = (page - 1) * limit
    end = start + limit
    return SearchPage(results=results[start:end], total=total, pages=pages)
