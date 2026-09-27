"""Movie details (poster, rating, plot, links) from the TMDB v3 API.

Answers, including misses, are cached for a week in the settings table under
`tmdb:` keys so repeat lookups don't use up the rate limit.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

import requests

import db
from search.ranking import normalize_title
from utils.logger import setup_logger

logger = setup_logger("providers.tmdb")

_BASE = "https://api.themoviedb.org/3"
_IMG_BASE = "https://image.tmdb.org/t/p"
_TIMEOUT = 6.0
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def get_api_key() -> Optional[str]:
    key = db.get_setting("tmdb_api_key")
    if key:
        key = key.strip()
        if key:
            return key
    env = os.environ.get("TMDB_API_KEY")
    if env:
        env = env.strip()
        if env:
            return env
    return None


def extract_year(title: str, fallback_date: str | None = None) -> Optional[int]:
    for candidate in (title, fallback_date or ""):
        if not candidate:
            continue
        match = _YEAR_RE.search(candidate)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
    return None


def enrich(title: str, year: Optional[int] = None) -> Optional[dict]:
    """Return TMDB details for a movie (keys as built in `_fetch_details`).

    Runtime is in minutes. Returns None when there is no API key, no match, or the
    request fails.
    """
    if not title:
        return None
    key = get_api_key()
    if not key:
        return None

    norm_key = _cache_key(title, year)
    cached = _read_cache(norm_key)
    if cached is not None:
        return cached or None

    try:
        params = {"api_key": key, "query": title, "include_adult": "false"}
        if year:
            params["year"] = year
        response = requests.get(f"{_BASE}/search/movie", params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        results = response.json().get("results") or []
    except Exception as exc:
        logger.warning(f"TMDB search failed for {title!r}: {exc}")
        return None

    best = _pick_best_match(results, title, year)
    if not best:
        _write_cache(norm_key, {})
        return None

    enriched = _fetch_details(best["id"], key) or _from_search_row(best)
    _write_cache(norm_key, enriched)
    return enriched


def _pick_best_match(results: list[dict], title: str, year: Optional[int]) -> Optional[dict]:
    if not results:
        return None
    target = normalize_title(title)
    if year:
        for row in results:
            if (row.get("release_date") or "").startswith(str(year)):
                return row
    for row in results:
        if normalize_title(row.get("title") or "") == target:
            return row
    return results[0]


def _fetch_details(tmdb_id: int, api_key: str) -> Optional[dict]:
    try:
        response = requests.get(
            f"{_BASE}/movie/{tmdb_id}",
            params={"api_key": api_key, "append_to_response": "videos,external_ids"},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning(f"TMDB details failed for {tmdb_id}: {exc}")
        return None

    return {
        "tmdbId": data.get("id"),
        "title": data.get("title") or "",
        "year": _year_from_date(data.get("release_date")),
        "rating": float(data.get("vote_average") or 0.0),
        "runtime": int(data.get("runtime") or 0),
        "genres": [g["name"] for g in (data.get("genres") or []) if g.get("name")],
        "plot": data.get("overview") or "",
        "poster": _image_url(data.get("poster_path"), "w342"),
        "backdrop": _image_url(data.get("backdrop_path"), "w780"),
        "trailerUrl": _pick_trailer(data.get("videos") or {}),
        "imdbId": (data.get("external_ids") or {}).get("imdb_id"),
        "imdbUrl": _imdb_url((data.get("external_ids") or {}).get("imdb_id")),
    }


def _from_search_row(row: dict) -> dict:
    return {
        "tmdbId": row.get("id"),
        "title": row.get("title") or "",
        "year": _year_from_date(row.get("release_date")),
        "rating": float(row.get("vote_average") or 0.0),
        "runtime": 0,
        "genres": [],
        "plot": row.get("overview") or "",
        "poster": _image_url(row.get("poster_path"), "w342"),
        "backdrop": _image_url(row.get("backdrop_path"), "w780"),
        "trailerUrl": None,
        "imdbId": None,
        "imdbUrl": None,
    }


def _image_url(path: Optional[str], size: str) -> Optional[str]:
    if not path:
        return None
    return f"{_IMG_BASE}/{size}{path}"


def _pick_trailer(videos: dict) -> Optional[str]:
    for video in videos.get("results", []) or []:
        if video.get("site") == "YouTube" and video.get("type") == "Trailer":
            return f"https://www.youtube.com/watch?v={video.get('key')}"
    return None


def _imdb_url(imdb_id: Optional[str]) -> Optional[str]:
    if not imdb_id:
        return None
    return f"https://www.imdb.com/title/{imdb_id}/"


def _year_from_date(date: Optional[str]) -> Optional[int]:
    if not date:
        return None
    match = _YEAR_RE.search(date)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _cache_key(title: str, year: Optional[int]) -> str:
    base = normalize_title(title) or title.lower()
    suffix = f":{year}" if year else ""
    return f"tmdb:{base}{suffix}"


def _read_cache(key: str) -> Optional[dict]:
    raw = db.get_setting(key)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    fetched_at = payload.get("_fetched_at") or 0
    if time.time() - fetched_at > _CACHE_TTL_SECONDS:
        return None
    if "data" in payload:
        return payload["data"] or {}
    return None


def _write_cache(key: str, data: dict | None) -> None:
    db.set_setting(key, json.dumps({"_fetched_at": time.time(), "data": data or {}}))
