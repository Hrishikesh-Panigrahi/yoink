"""Enums replacing magic strings used by the search layer."""

from __future__ import annotations

from enum import Enum
from typing import Iterable


class ProviderMode(str, Enum):
    """How searches should be sourced."""

    STABLE = "stable"  # direct YTS + Pirate Bay APIs (default, reliable)
    MULTI = "multi"    # vendored Torrent-Api-py scrapers across many sites

    @classmethod
    def from_value(cls, value: str | None) -> "ProviderMode":
        if not value:
            return cls.STABLE
        try:
            return cls(value.lower())
        except ValueError:
            return cls.STABLE


class Region(str, Enum):
    """Cultural region used to expand queries and bias ranking."""

    ANY = "any"
    BOLLYWOOD = "bollywood"
    HOLLYWOOD = "hollywood"
    SOUTH_INDIAN = "south-indian"
    KOREAN = "korean"
    ANIME = "anime"

    @classmethod
    def from_value(cls, value: str | None) -> "Region":
        if not value:
            return cls.ANY
        try:
            return cls(value.lower())
        except ValueError:
            return cls.ANY


class Category(str, Enum):
    """Content category passed through to category-aware providers."""

    ANY = "any"
    MOVIES = "movies"
    TV = "tv"
    ANIME = "anime"
    MUSIC = "music"
    GAMES = "games"
    APPS = "apps"
    BOOKS = "books"

    @classmethod
    def from_value(cls, value: str | None) -> "Category":
        if not value:
            return cls.MOVIES
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MOVIES


REGION_TERMS: dict[Region, tuple[str, ...]] = {
    Region.ANY: (),
    Region.BOLLYWOOD: ("hindi", "bollywood", "desi"),
    Region.HOLLYWOOD: ("english", "hollywood"),
    Region.SOUTH_INDIAN: ("tamil", "telugu", "malayalam", "kannada", "south"),
    Region.KOREAN: ("korean", "kdrama", "k-drama"),
    Region.ANIME: ("anime", "sub", "dub"),
}


def region_terms(region: Region) -> Iterable[str]:
    """Return the search/score booster terms for a region."""
    return REGION_TERMS.get(region, ())
