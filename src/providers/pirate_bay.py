from __future__ import annotations

import time
from datetime import datetime
from typing import List

import requests

from search.dto import SearchResult
from search.enums import Category
from utils.format import format_size
from utils.logger import setup_logger
from utils.magnets import build_magnet

logger = setup_logger("providers.pirate_bay")

PIRATE_BAY_BASE_URL = "https://apibay.org"
_MIN_REQUEST_INTERVAL = 1.0
_last_request_time = 0.0

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
}


# The Pirate Bay's category numbers for each of ours. A top-level code such as
# "400" also covers everything under it (401, 402, ...).
_CATEGORY_CODES = {
    Category.MOVIES: ("201", "202", "207", "209", "210", "211"),
    Category.TV: ("205", "208", "212"),
    # There is no anime category, so anime means any film or TV category.
    Category.ANIME: ("201", "202", "205", "207", "208", "209", "211", "212", "299"),
    Category.MUSIC: ("101", "104", "203"),
    Category.GAMES: ("400",),
    Category.APPS: ("300",),
    Category.BOOKS: ("102", "601", "602"),
}


def _in_category(code: str, codes: tuple[str, ...]) -> bool:
    return any(code == c or (c.endswith("00") and code[:1] == c[:1]) for c in codes)


def _throttle() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def search_pirate_bay(
    query: str, page: int = 1, limit: int = 20, category: Category = Category.ANY
) -> List[SearchResult]:
    _throttle()

    codes = _CATEGORY_CODES.get(category, ())
    url = f"{PIRATE_BAY_BASE_URL}/q.php"
    params = {"q": query, "cat": ",".join(codes) or "0", "page": str(page), "limit": str(limit)}
    try:
        response = requests.get(url, params=params, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.error(f"Pirate Bay request failed: {exc}")
        return []

    if not isinstance(data, list):
        logger.warning("Pirate Bay returned non-list payload")
        return []

    results: List[SearchResult] = []
    for item in data:
        info_hash = item.get("info_hash") or ""
        # When nothing matches, apibay returns one placeholder row named
        # "No results returned" with an all-zero info_hash.
        if not info_hash or set(info_hash) <= {"0"}:
            continue
        if (item.get("name") or "").strip().lower() == "no results returned":
            continue
        # apibay already filters by `cat`; this keeps out anything it lets through.
        code = str(item.get("category") or "")
        if codes and code and not _in_category(code, codes):
            continue
        try:
            results.append(
                SearchResult(
                    title=item["name"],
                    size=format_size(int(item.get("size") or 0)),
                    seeds=int(item.get("seeders") or 0),
                    peers=int(item.get("leechers") or 0),
                    date=datetime.fromtimestamp(int(item.get("added") or 0)).strftime("%Y-%m-%d"),
                    source="The Pirate Bay",
                    magnet_url=build_magnet(info_hash, item["name"]),
                )
            )
        except (KeyError, ValueError) as exc:
            logger.warning(f"Skipping malformed Pirate Bay row: {exc}")
    return results
