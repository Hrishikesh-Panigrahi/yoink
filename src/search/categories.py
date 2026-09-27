"""Work out which Category a result belongs to, for sources that can't filter by category."""

from __future__ import annotations

import re
from typing import Optional

from search.enums import Category

ADULT = "adult"
# A site that only says "Video" could mean a film or a show.
VIDEO = "video"

_LABEL_RULES = (
    (ADULT, r"xxx|porn|adult"),
    (Category.ANIME, r"anime"),
    (Category.BOOKS, r"books?|e-?books?|comics?|literature|magazines?"),
    (Category.GAMES, r"games?"),
    (Category.APPS, r"apps?|applications?|software|programs?"),
    (Category.TV, r"tv|television|series|shows?|episodes?"),
    (Category.MOVIES, r"movies?|films?|documentar(?:y|ies)"),
    (VIDEO, r"video"),
    (Category.MUSIC, r"music|audio|lossless|flac|mp3|albums?"),
)

# Only strong signals: a title that matches none of these stays unclassified.
_TITLE_RULES = (
    (ADULT, r"\b(?:xxx|porn)\b"),
    (Category.BOOKS, r"\b(?:epub|mobi|azw3|e-?books?|audiobooks?|comics?|cbr|cbz)\b"),
    (Category.GAMES, r"\b(?:repack|fitgirl|dodi|elamigos|gog|codex|plaza|skidrow|empress"
                     r"|tenoke|pc game|ps[345]|nsw)\b"),
    (Category.ANIME, r"^\[(?:subsplease|erai-raws|horriblesubs|judas|ember|asw|commie"
                     r"|yameii|tsundere-raws|toonshub)\]"),
    (Category.TV, r"\bs\d{1,2}e\d{1,3}\b|\bseason \d+\b|\b\d{1,2}x\d{2}\b"),
    (Category.MUSIC, r"\b(?:flac|mp3|320 ?kbps|discography|album|ost|soundtrack)\b"),
    (Category.APPS, r"\b(?:x64|x86|macos|portable|keygen|activator|pre-?activated"
                    r"|windows (?:7|8|10|11))\b"),
    (Category.MOVIES, r"\b(?:19|20)\d{2}\b.*\b(?:2160p|1080p|720p|480p|bluray|blu-ray|brrip"
                      r"|bdrip|web-?dl|webrip|dvdrip|hdrip|x26[45]|hevc)\b"),
)

_ACCEPTS = {
    Category.MOVIES: {Category.MOVIES, VIDEO},
    Category.TV: {Category.TV, VIDEO},
    Category.ANIME: {Category.ANIME, Category.TV, Category.MOVIES, VIDEO},
    Category.MUSIC: {Category.MUSIC},
    Category.GAMES: {Category.GAMES},
    Category.APPS: {Category.APPS},
    Category.BOOKS: {Category.BOOKS},
}


def from_label(label: str) -> Optional[str]:
    text = (label or "").lower()
    for category, pattern in _LABEL_RULES:
        if re.search(rf"\b(?:{pattern})\b", text):
            return category
    return None


def from_title(title: str) -> Optional[str]:
    text = (title or "").lower()
    for category, pattern in _TITLE_RULES:
        if re.search(pattern, text):
            return category
    return None


def classify(label: str, title: str) -> Optional[str]:
    """The site's own label wins; the title only fills in (or narrows "Video")."""
    found = from_label(label)
    if found in (None, VIDEO):
        guess = from_title(title)
        if found is None or guess in (Category.MOVIES, Category.TV, Category.ANIME):
            found = guess or found
    return found


def matches(category: Category, label: str = "", title: str = "") -> bool:
    """Whether a result belongs in `category`. Results that can't be classified are kept."""
    if category is Category.ANY:
        return True
    found = classify(label, title)
    return found is None or found in _ACCEPTS[category]
