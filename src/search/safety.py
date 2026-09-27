"""Rough safety hints for search results.

The checks look only at the result's own fields. Nothing is downloaded or scanned.
"""

from __future__ import annotations

import re
from typing import List

_RISKY_KEYWORDS = (
    ".exe",
    ".scr",
    ".msi",
    ".bat",
    ".cmd",
    "installer",
    "setup.exe",
    "keygen",
    "crack.exe",
    "rar password",
    "password.txt",
    "watch-online",
    "click here",
    "join group",
)
_PROMO_KEYWORDS = (
    "telegram",
    "watch in",
    "subscribe",
    "join our",
)
_GOOD_GROUPS = ("rarbg", "yts", "yify", "evo", "fitgirl", "sparks", "qxr", "tigole", "fgt")

_SIZE_RE = re.compile(r"([\d.]+)\s*(KB|MB|GB|TB)", re.I)


def evaluate(result_dict: dict) -> dict:
    """Rate a serialized SearchResult as safe, caution or risky, with up to four reasons."""
    reasons: List[str] = []
    score = 100  # higher = safer

    title = (result_dict.get("title") or "").lower()
    source = (result_dict.get("source") or "").lower()
    seeds = int(result_dict.get("seeds") or 0)
    size_bytes = _size_to_bytes(result_dict.get("size") or "")

    for kw in _RISKY_KEYWORDS:
        if kw in title:
            reasons.append(f"Title mentions '{kw}'")
            score -= 40
    for kw in _PROMO_KEYWORDS:
        if kw in title:
            reasons.append("Title contains promo / spam text")
            score -= 15
            break

    if seeds <= 0:
        reasons.append("No seeders, so it may never finish")
        score -= 30
    elif seeds < 3:
        reasons.append(f"Very low seeders ({seeds})")
        score -= 10

    if (
        size_bytes
        and size_bytes < 50 * 1024 * 1024
        and "music" not in title
        and "ebook" not in title
    ):
        reasons.append("Unusually small file (under 50 MB)")
        score -= 25

    if size_bytes and size_bytes > 40 * 1024 * 1024 * 1024:
        reasons.append("Very large file (over 40 GB)")
        score -= 5

    if any(group in title for group in _GOOD_GROUPS) or source in {"yts", "the pirate bay"}:
        score += 15
        reasons.append("Trusted release group / source")

    if not result_dict.get("magnet"):
        reasons.append("Missing magnet link")
        score -= 50

    if score >= 90:
        level = "safe"
    elif score >= 55:
        level = "caution"
    else:
        level = "risky"

    return {"level": level, "reasons": reasons[:4]}


def _size_to_bytes(size_str: str) -> int:
    match = _SIZE_RE.search(size_str)
    if not match:
        return 0
    try:
        amount = float(match.group(1))
    except ValueError:
        return 0
    unit = match.group(2).upper()
    scale = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}.get(unit, 1)
    return int(amount * scale)
