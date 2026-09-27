from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from search.enums import Category, ProviderMode, Quality, Region, SortBy


@dataclass(frozen=True)
class SearchResult:
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
        from search.safety import evaluate as evaluate_safety

        payload = self._raw_dict()
        payload["safety"] = evaluate_safety(payload)
        return payload

    def _raw_dict(self) -> dict:
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
    provider_mode: ProviderMode = ProviderMode.STABLE
    region: Region = Region.ANY
    category: Category = Category.MOVIES
    quality: Quality = Quality.ANY
    sort_by: SortBy = SortBy.RELEVANCE
    min_seeds: int = 0
    sites: Optional[List[str]] = None
    limit_per_site: int = 5
    # Any of "yts" and "piratebay_stable". None means both are on.
    enabled_stable: Optional[List[str]] = None

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
        try:
            min_seeds = max(0, int(data.get("minSeeds") or 0))
        except (TypeError, ValueError):
            min_seeds = 0
        enabled_stable_raw = data.get("enabledStable")
        if isinstance(enabled_stable_raw, list):
            enabled_stable = [str(s) for s in enabled_stable_raw if s]
        elif isinstance(enabled_stable_raw, str):
            enabled_stable = [s.strip() for s in enabled_stable_raw.split(",") if s.strip()]
        else:
            enabled_stable = None
        return cls(
            provider_mode=ProviderMode.from_value(data.get("providerMode")),
            region=Region.from_value(data.get("region")),
            category=Category.from_value(data.get("category") or data.get("contentType")),
            quality=Quality.from_value(data.get("quality")),
            sort_by=SortBy.from_value(data.get("sortBy")),
            min_seeds=min_seeds,
            sites=sites,
            limit_per_site=limit_per_site,
            enabled_stable=enabled_stable,
        )


@dataclass(frozen=True)
class SearchPage:
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
