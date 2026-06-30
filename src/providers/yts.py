"""YTS.mx movie API adapter — module-level function."""

from __future__ import annotations

from datetime import datetime
from typing import List

import requests

from search.dto import SearchResult
from utils.logger import setup_logger
from utils.magnets import build_magnet

logger = setup_logger("providers.yts")

YTS_BASE_URL = "https://yts.mx/api/v2"
YTS_TRACKERS = (
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:80",
    "udp://tracker.coppersurfer.tk:6969",
    "udp://glotorrents.pw:6969/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://torrent.gresille.org:80/announce",
    "udp://p4p.arenabg.com:1337",
    "udp://tracker.leechers-paradise.org:6969",
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "application/json",
}


def search_yts(query: str, limit: int = 20) -> List[SearchResult]:
    """Search YTS for movies and return one `SearchResult` per quality."""
    url = f"{YTS_BASE_URL}/list_movies.json"
    params = {
        "query_term": query,
        "limit": limit,
        "sort_by": "download_count",
        "order_by": "desc",
        "with_rt_ratings": True,
    }

    try:
        response = requests.get(url, params=params, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.error(f"YTS request failed: {exc}")
        return []

    if data.get("status") != "ok":
        logger.warning(f"YTS API error: {data.get('status_message')}")
        return []

    movies = (data.get("data") or {}).get("movies") or []
    results: List[SearchResult] = []
    for movie in movies:
        torrents = movie.get("torrents") or []
        torrents.sort(key=lambda t: int(t.get("seeds", 0) or 0), reverse=True)
        for torrent in torrents:
            info_hash = torrent.get("hash")
            quality = torrent.get("quality") or "Unknown"
            if not info_hash:
                continue
            results.append(
                SearchResult(
                    title=f"{movie.get('title')} ({movie.get('year')}) [{quality}]",
                    size=torrent.get("size") or "Unknown",
                    seeds=int(torrent.get("seeds", 0) or 0),
                    peers=int(torrent.get("peers", 0) or 0),
                    date=str(movie.get("year") or datetime.now().year),
                    source="YTS",
                    magnet_url=build_magnet(
                        info_hash,
                        f"{movie.get('title')} {quality}",
                        trackers=YTS_TRACKERS,
                    ),
                    quality=quality,
                    year=int(movie.get("year") or 0) or None,
                    rating=float(movie.get("rating") or 0) or None,
                    summary=(movie.get("summary") or movie.get("synopsis") or "").strip(),
                    runtime=int(movie.get("runtime") or 0),
                    genres=list(movie.get("genres") or []),
                    cover_image=(
                        movie.get("large_cover_image")
                        or movie.get("medium_cover_image")
                        or movie.get("small_cover_image")
                        or ""
                    ),
                    imdb_code=movie.get("imdb_code") or "",
                    language=movie.get("language") or "",
                )
            )
    return results
