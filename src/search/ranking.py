from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, List

from search.dto import SearchResult
from search.enums import Quality, Region, SortBy, region_terms

# Multipliers on health_score, so curated sources rank a little above scrapers.
SOURCE_WEIGHTS: dict[str, float] = {
    "the pirate bay": 1.05,
    "1337x": 1.0,
    "nyaa": 1.0,
}

_QUALITY_TOKENS = (
    "2160p", "1080p", "720p", "480p",
    "x265", "x264", "hevc", "h265", "h264",
    "webrip", "web-dl", "webdl", "bluray", "blu-ray", "brrip", "bdrip",
    "hdrip", "dvdrip", "hdcam", "cam", "ts", "telesync",
    "10bit", "8bit", "hdr", "dolby", "atmos", "aac", "ac3", "dts",
    "amzn", "nf", "hulu",
)

_RELEASE_GROUPS = (
    "rarbg", "yts", "ettv", "eztv", "fgt", "psa", "ion10", "sparks", "fum",
    "mzabi", "qxr", "nogrp", "tigole", "geckos", "cmrg", "joy", "edge2020",
    "silence", "fitgirl", "kaos", "fitgr1",
)

_RELEASE_GROUP_RE = re.compile(
    r"[-.](?:" + "|".join(map(re.escape, _RELEASE_GROUPS)) + r")\w*$", re.I
)
_TRAIL_NOISE_RE = re.compile(r"[\[\(\{][^\[\(\{]*[\]\)\}]")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_TITLE_QUALITY_RE = re.compile(
    r"\b(" + "|".join(map(re.escape, _QUALITY_TOKENS)) + r")\b", re.I
)


def expand_region_queries(query: str, region: Region) -> List[str]:
    base = (query or "").strip()
    if not base:
        return []
    queries = [base]
    lowered = base.lower()
    for term in region_terms(region):
        if term not in lowered:
            queries.append(f"{base} {term}")
    return queries


def normalize_title(title: str) -> str:
    """Reduce a release title to the bare name, for use as a dedupe key."""
    if not title:
        return ""
    text = title.lower()
    text = _TRAIL_NOISE_RE.sub(" ", text)
    text = _TITLE_QUALITY_RE.sub(" ", text)
    text = _RELEASE_GROUP_RE.sub(" ", text)
    text = _YEAR_RE.sub(" ", text)
    text = _NON_WORD_RE.sub(" ", text)
    return " ".join(text.split())


def dedupe_results(results: Iterable[SearchResult]) -> List[SearchResult]:
    """Dedupe by magnet URL, then by normalized title, keeping the one with most seeds."""
    by_key: dict[str, SearchResult] = {}
    for result in results:
        magnet_key = (result.magnet_url or "").lower()
        if magnet_key and magnet_key in by_key:
            if result.seeds > by_key[magnet_key].seeds:
                by_key[magnet_key] = result
            continue
        if magnet_key:
            by_key[magnet_key] = result

    second_pass: dict[str, SearchResult] = {}
    for result in by_key.values():
        title_key = normalize_title(result.title)
        if not title_key:
            second_pass[result.magnet_url or result.title] = result
            continue
        existing = second_pass.get(title_key)
        if existing is None or _replacement_score(result, existing) > 0:
            second_pass[title_key] = result
    return list(second_pass.values())


def _replacement_score(new: SearchResult, existing: SearchResult) -> int:
    """Positive if `new` should replace `existing`: more seeds wins, then higher quality."""
    if new.seeds != existing.seeds:
        return 1 if new.seeds > existing.seeds else -1
    new_q = _quality_rank(new.quality or "")
    old_q = _quality_rank(existing.quality or "")
    return 1 if new_q > old_q else -1


def _quality_rank(quality: str) -> int:
    q = (quality or "").lower()
    if "2160" in q:
        return 4
    if "1080" in q:
        return 3
    if "720" in q:
        return 2
    if "480" in q:
        return 1
    return 0


def health_score(result: SearchResult, query: str, region: Region) -> float:
    """Relevance score for the default sort. Higher is better, roughly 0 to 500."""
    title = (result.title or "").lower()
    tokens = [tok for tok in (query or "").lower().split() if tok]
    score = sum(100 for tok in tokens if tok in title)
    if query and query.lower() in title:
        score += 150

    haystack = " ".join(
        [
            result.title or "",
            result.source or "",
            result.language or "",
            " ".join(result.genres or []),
            result.summary or "",
        ]
    ).lower()
    score += sum(60 for term in region_terms(region) if term in haystack)

    score += min(result.seeds, 5000) / 50
    score += min(result.peers, 5000) / 100

    source_weight = SOURCE_WEIGHTS.get((result.source or "").lower(), 0.9)
    score *= source_weight

    score += _recency_bonus(result.date)
    score += _quality_rank(result.quality or "") * 2

    return score


def _recency_bonus(date_str: str | None) -> float:
    if not date_str:
        return 0.0
    match = _YEAR_RE.search(date_str)
    if not match:
        return 0.0
    try:
        year = int(match.group(1))
    except ValueError:
        return 0.0
    delta = datetime.now().year - year
    if delta < 0:
        return 0.0
    return max(0.0, 10.0 - delta * 2.0)


def filter_by_quality(results: List[SearchResult], quality: Quality) -> List[SearchResult]:
    if quality is Quality.ANY:
        return results
    needle = quality.value.lower()
    filtered: List[SearchResult] = []
    for result in results:
        haystack = f"{result.quality or ''} {result.title or ''}".lower()
        if needle in haystack:
            filtered.append(result)
    return filtered


def filter_by_min_seeds(results: List[SearchResult], min_seeds: int) -> List[SearchResult]:
    if not min_seeds:
        return results
    return [r for r in results if (r.seeds or 0) >= min_seeds]


def sort_results(
    results: List[SearchResult],
    sort_by: SortBy,
    query: str,
    region: Region,
) -> List[SearchResult]:
    if sort_by is SortBy.SEEDS:
        return sorted(results, key=lambda r: r.seeds or 0, reverse=True)
    if sort_by is SortBy.NEWEST:
        return sorted(results, key=_date_key, reverse=True)
    if sort_by is SortBy.SIZE:
        return sorted(results, key=lambda r: _size_to_bytes(r.size), reverse=True)
    return sorted(results, key=lambda r: health_score(r, query, region), reverse=True)


def _date_key(result: SearchResult) -> tuple[int, int]:
    if not result.date:
        return (0, result.seeds or 0)
    match = _YEAR_RE.search(result.date)
    if not match:
        return (0, result.seeds or 0)
    try:
        return (int(match.group(1)), result.seeds or 0)
    except ValueError:
        return (0, result.seeds or 0)


_SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
_SIZE_RE = re.compile(r"([\d.]+)\s*([KMGT]?B)", re.I)


def _size_to_bytes(size_str: str | None) -> float:
    if not size_str:
        return 0.0
    match = _SIZE_RE.search(size_str)
    if not match:
        return 0.0
    try:
        amount = float(match.group(1))
    except ValueError:
        return 0.0
    unit = match.group(2).upper()
    return amount * _SIZE_UNITS.get(unit, 1)
