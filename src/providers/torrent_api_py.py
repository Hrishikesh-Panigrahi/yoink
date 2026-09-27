"""Runs the vendored Torrent-Api-py scrapers (src/vendor/torrent_api_py) in-process.

Upstream is a FastAPI service. We call its per-site async classes directly instead.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional

from search.dto import SearchResult
from search.enums import Category, Region, region_terms
from utils.logger import setup_logger

logger = setup_logger("providers.torrent_api_py")


def _vendor_root() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path.cwd())) / "vendor" / "torrent_api_py"
    else:
        base = Path(__file__).resolve().parents[1] / "vendor" / "torrent_api_py"
    return base


_VENDOR_ROOT = _vendor_root()


def _load_vendored_sites() -> dict:
    """Import the vendored site registry without shadowing our own `torrents` package.

    The vendored code has its own top-level `torrents` package. While it imports, the
    vendor root goes first on sys.path and our `torrents` modules are taken out of
    sys.modules. Afterwards the vendored `torrents.*` modules are dropped and ours
    are put back, so a later `import torrents` still gets ours.
    """
    if not _VENDOR_ROOT.exists():
        return {}

    vendor_path = str(_VENDOR_ROOT)
    sys.path.insert(0, vendor_path)

    stashed = {name: mod for name, mod in sys.modules.items()
               if name == "torrents" or name.startswith("torrents.")}
    for name in stashed:
        sys.modules.pop(name, None)

    before = set(sys.modules)
    try:
        from helper.is_site_available import all_sites  # type: ignore
        return dict(all_sites)
    except Exception as exc:  # pragma: no cover
        logger.error(f"Unable to import vendored torrent providers: {exc}")
        return {}
    finally:
        # Keep the vendor root on the path, but last, so it can't shadow our packages.
        try:
            sys.path.remove(vendor_path)
        except ValueError:
            pass
        if vendor_path not in sys.path:
            sys.path.append(vendor_path)

        for name in set(sys.modules) - before:
            if name == "torrents" or name.startswith("torrents."):
                sys.modules.pop(name, None)
        sys.modules.update(stashed)


_VENDORED_SITES = _load_vendored_sites()

#: Tests monkeypatch this.
AVAILABLE_SITES: Dict[str, dict] = dict(_VENDORED_SITES)

DEFAULT_SITES: tuple[str, ...] = (
    "1337x",
    "tgx",
    "torlock",
    "kickass",
    "limetorrent",
    "torrentfunk",
    "bitsearch",
    "magnetdl",
    "yts",
    "piratebay",
)

_CATEGORY_FOR_VENDOR = {
    Category.ANY: "",
    Category.MOVIES: "movies",
    Category.TV: "tv",
    Category.ANIME: "anime",
    Category.MUSIC: "music",
    Category.GAMES: "games",
    Category.APPS: "apps",
    Category.BOOKS: "books",
}


def available_sites() -> Dict[str, dict]:
    return AVAILABLE_SITES


def site_configs() -> Dict[str, dict]:
    configs: Dict[str, dict] = {}
    for key, cfg in AVAILABLE_SITES.items():
        configs[key] = {
            "name": getattr(cfg.get("website"), "_name", key),
            "categories": cfg.get("categories", []),
            "searchByCategory": bool(cfg.get("search_by_category")),
            "limit": int(cfg.get("limit", 20) or 20),
        }
    return configs


def search_multi_site(
    query: str,
    page: int = 1,
    sites: Optional[List[str]] = None,
    category: Category = Category.MOVIES,
    region: Region = Region.ANY,
    limit_per_site: int = 5,
    timeout_seconds: float = 12.0,
) -> List[SearchResult]:
    """Search the sites concurrently, best match first. `sites=None` means DEFAULT_SITES."""
    if not AVAILABLE_SITES:
        return []
    return asyncio.run(
        _search_all(query, page, sites, category, region, limit_per_site, timeout_seconds)
    )


async def _search_all(
    query: str,
    page: int,
    sites: Optional[List[str]],
    category: Category,
    region: Region,
    limit_per_site: int,
    timeout_seconds: float,
) -> List[SearchResult]:
    selected = sites or list(DEFAULT_SITES)
    tasks = [
        _search_one(site, query, page, category, region, limit_per_site, timeout_seconds)
        for site in selected
        if site in AVAILABLE_SITES
    ]
    if not tasks:
        return []
    scored: List[tuple[float, SearchResult]] = []
    for result in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(result, Exception):
            logger.warning(f"Vendored provider error: {result}")
            continue
        scored.extend(result)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored]


async def _search_one(
    site: str,
    query: str,
    page: int,
    category: Category,
    region: Region,
    limit_per_site: int,
    timeout_seconds: float,
) -> List[tuple[float, SearchResult]]:
    cfg = AVAILABLE_SITES[site]
    provider_cls = cfg["website"]
    limit = min(max(1, limit_per_site), int(cfg.get("limit", 20) or 20))
    vendor_category = _CATEGORY_FOR_VENDOR.get(category, "")

    provider = provider_cls()
    try:
        if (
            vendor_category
            and cfg.get("search_by_category")
            and vendor_category in (cfg.get("categories") or [])
            and hasattr(provider, "search_by_category")
        ):
            response = await asyncio.wait_for(
                provider.search_by_category(query, vendor_category, page, limit),
                timeout=timeout_seconds,
            )
        else:
            response = await asyncio.wait_for(
                provider.search(query, page, limit),
                timeout=timeout_seconds,
            )
    except Exception as exc:
        logger.warning(f"{site} search failed: {exc}")
        return []

    if not isinstance(response, dict):
        return []
    data = response.get("data") or []
    source_name = site_configs().get(site, {}).get("name", site)
    out: List[tuple[float, SearchResult]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        result = _row_to_result(item, source_name)
        if not result.title or not result.magnet_url:
            continue
        score = _score_vendor_row(item, query, region, category, result)
        out.append((score, result))
    return out


def _row_to_result(item: dict, source: str) -> SearchResult:
    title = str(item.get("name") or item.get("title") or "").strip()
    genres = item.get("genre") or item.get("genres") or []
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.replace("/", ",").split(",") if g.strip()]
    return SearchResult(
        title=title,
        size=str(item.get("size") or "Unknown"),
        seeds=_to_int(item.get("seeders") or item.get("seeds")),
        peers=_to_int(item.get("leechers") or item.get("peers")),
        date=str(item.get("date") or ""),
        source=source,
        magnet_url=str(item.get("magnet") or item.get("magnet_url") or ""),
        quality=_extract_quality(title) or None,
        summary=str(item.get("description") or item.get("summary") or ""),
        runtime=_parse_runtime(item.get("runtime")),
        genres=list(genres),
        cover_image=str(item.get("poster") or item.get("cover") or ""),
        imdb_code=str(item.get("imdb_id") or item.get("imdb_code") or ""),
        language=str(item.get("language") or ""),
    )


def _score_vendor_row(
    item: dict, query: str, region: Region, category: Category, result: SearchResult
) -> float:
    title_l = result.title.lower()
    tokens = [tok for tok in query.lower().split() if tok]
    score = sum(100 for tok in tokens if tok in title_l)
    if query.lower() in title_l:
        score += 150
    haystack = " ".join(
        str(item.get(k) or "")
        for k in ("name", "title", "category", "language", "description", "summary")
    ).lower()
    score += sum(50 for term in region_terms(region) if term in haystack)
    vendor_category = _CATEGORY_FOR_VENDOR.get(category, "")
    if vendor_category and vendor_category in str(item.get("category") or "").lower():
        score += 35
    score += min(result.seeds, 5000) / 50
    return score


def _to_int(value) -> int:
    try:
        if value is None:
            return 0
        cleaned = str(value).strip().replace(",", "")
        if cleaned.endswith("K"):
            return int(float(cleaned[:-1]) * 1000)
        return int(float(cleaned))
    except (TypeError, ValueError):
        return 0


def _extract_quality(title: str) -> str:
    lowered = title.lower()
    for quality in ("2160p", "1080p", "720p", "480p", "x265", "x264"):
        if quality in lowered:
            return quality
    return ""


def _parse_runtime(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value or "").lower()
    if not text:
        return 0
    hours = 0
    minutes = 0
    for part in text.replace("hrs", "h").replace("hr", "h").split():
        if part.endswith("h"):
            try:
                hours = int(part[:-1])
            except ValueError:
                pass
        elif part.endswith("m") or part.endswith("min"):
            try:
                minutes = int(part.rstrip("min").rstrip("m"))
            except ValueError:
                pass
    return hours * 60 + minutes
