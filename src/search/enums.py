from __future__ import annotations

from enum import Enum
from typing import Iterable


class ProviderMode(str, Enum):
    STABLE = "stable"  # The Pirate Bay's JSON API
    MULTI = "multi"    # vendored Torrent-Api-py site scrapers

    @classmethod
    def from_value(cls, value: str | None) -> "ProviderMode":
        if not value:
            return cls.STABLE
        try:
            return cls(value.lower())
        except ValueError:
            return cls.STABLE


class Region(str, Enum):
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
            return cls.ANY
        try:
            return cls(value.lower())
        except ValueError:
            return cls.ANY


class Quality(str, Enum):
    ANY = "any"
    UHD_2160P = "2160p"
    FHD_1080P = "1080p"
    HD_720P = "720p"
    SD_480P = "480p"
    X265 = "x265"
    X264 = "x264"

    @classmethod
    def from_value(cls, value: str | None) -> "Quality":
        if not value:
            return cls.ANY
        try:
            return cls(value.lower())
        except ValueError:
            return cls.ANY


class SortBy(str, Enum):
    RELEVANCE = "relevance"  # sorts by ranking.health_score
    SEEDS = "seeds"
    SIZE = "size"
    NEWEST = "newest"

    @classmethod
    def from_value(cls, value: str | None) -> "SortBy":
        if not value:
            return cls.RELEVANCE
        try:
            return cls(value.lower())
        except ValueError:
            return cls.RELEVANCE


REGION_TERMS: dict[Region, tuple[str, ...]] = {
    Region.ANY: (),
    Region.BOLLYWOOD: ("hindi", "bollywood", "desi"),
    Region.HOLLYWOOD: ("english", "hollywood"),
    Region.SOUTH_INDIAN: ("tamil", "telugu", "malayalam", "kannada", "south"),
    Region.KOREAN: ("korean", "kdrama", "k-drama"),
    Region.ANIME: ("anime", "sub", "dub"),
}


def region_terms(region: Region) -> Iterable[str]:
    return REGION_TERMS.get(region, ())
