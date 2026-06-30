"""DTOs that flow between providers, the search orchestrator, and the bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from search.enums import Category, ProviderMode, Region


@dataclass(frozen=True)
class SearchResult:
    """One torrent search hit, normalized across providers."""

    title: str
    size: str
    seeds: int
    peers: int
    date: str
    source: str
    magnet_url: str
    quality: Optional[str] = None
    year: Optional[int] = None
    rating: Optional[float] = None
    summary: str = ""
    runtime: int = 0
    genres: List[str] = field(default_factory=list)
    cover_image: str = ""
    imdb_code: str = ""
    language: str = ""

    def to_dict(self) -> dict:
        """JSON-friendly mapping used by the JS bridge."""
        return {
            "title": self.title,
            "size": self.size,
            "seeds": self.seeds,
            "peers": self.peers,
            "date": self.date,
            "source": self.source,
            "magnet": self.magnet_url,
            "quality": self.quality,
            "year": self.year,
            "rating": self.rating,
            "summary": self.summary,
            "runtime": self.runtime,
            "genres": list(self.genres or []),
            "cover": self.cover_image,
            "imdbCode": self.imdb_code,
            "language": self.language,
        }


@dataclass(frozen=True)
class SearchOptions:
    """User-controlled filters passed to the search orchestrator."""

    provider_mode: ProviderMode = ProviderMode.STABLE
    region: Region = Region.ANY
    category: Category = Category.MOVIES
    sites: Optional[List[str]] = None
    limit_per_site: int = 5

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "SearchOptions":
        data = data or {}
        sites_value = data.get("sites")
        if isinstance(sites_value, str):
            sites = [s.strip() for s in sites_value.split(",") if s.strip()]
        elif isinstance(sites_value, list):
            sites = [str(s) for s in sites_value if s]
        else:
            sites = None
        try:
            limit_per_site = int(data.get("limitPerSite") or 5)
        except (TypeError, ValueError):
            limit_per_site = 5
        return cls(
            provider_mode=ProviderMode.from_value(data.get("providerMode")),
            region=Region.from_value(data.get("region")),
            category=Category.from_value(data.get("category") or data.get("contentType")),
            sites=sites,
            limit_per_site=limit_per_site,
        )


@dataclass(frozen=True)
class SearchPage:
    """A single page of search results plus pagination metadata."""

    results: List[SearchResult]
    total: int
    pages: int

    def to_dict(self, query: str, page: int) -> dict:
        return {
            "query": query,
            "page": page,
            "results": [r.to_dict() for r in self.results],
            "total": self.total,
            "pages": self.pages,
        }
