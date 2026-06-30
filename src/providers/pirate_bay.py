"""apibay.org adapter for The Pirate Bay search."""

from __future__ import annotations

import time
from datetime import datetime
from typing import List

import requests

from search.dto import SearchResult
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


def _throttle() -> None:
    """Self-imposed 1s rate limit shared across calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def search_pirate_bay(query: str, page: int = 1, limit: int = 20) -> List[SearchResult]:
    """Search The Pirate Bay's JSON API and return normalized `SearchResult`s."""
    _throttle()

    url = f"{PIRATE_BAY_BASE_URL}/q.php"
    params = {"q": query, "cat": "0", "page": str(page), "limit": str(limit)}
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
        info_hash = item.get("info_hash")
        if not info_hash:
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
