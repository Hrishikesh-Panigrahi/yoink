"""Search functionality for torrents."""

import logging
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from src.utils.logger import setup_logger
from src.utils.pirate_bay import PirateBayAPI, PirateBayTorrent
from src.utils.yts_api import YTSAPI, YTSTorrent

logger = setup_logger('search')

@dataclass
class SearchResult:
    """Represents a search result from any source."""
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

class SearchUtil:
    """Handles searching across multiple torrent sources."""
    
    def __init__(self):
        """Initialize search utilities."""
        self.pirate_bay = PirateBayAPI()
        self.yts = YTSAPI()
    
    def search_torrents(self, query: str, page: int = 1, limit: int = 20) -> Tuple[List[SearchResult], int, int]:
        """Search for torrents across all sources.
        
        Args:
            query: Search query
            page: Page number (1-based)
            limit: Results per page
            
        Returns:
            Tuple of (results, total_results, total_pages)
        """
        try:
            # Search both sources
            pirate_results = self.pirate_bay.search(query, page, limit)
            yts_results = self.yts.search_movies(query, limit)
            
            # Convert YTS results to SearchResult objects
            yts_search_results = [
                SearchResult(
                    title=torrent.title,
                    size=torrent.size,
                    seeds=torrent.seeds,
                    peers=torrent.peers,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    source=torrent.source,
                    magnet_url=torrent.magnet_url,
                    quality=torrent.quality,
                    year=torrent.year,
                    rating=torrent.rating
                )
                for torrent in yts_results
            ]
            
            # Combine and sort all results by seeds
            all_results = pirate_results + yts_search_results
            all_results.sort(key=lambda x: (x.seeds, x.peers), reverse=True)
            
            # Calculate pagination
            total_results = len(all_results)
            total_pages = (total_results + limit - 1) // limit
            
            # Apply pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_results = all_results[start_idx:end_idx]
            
            return paginated_results, total_results, total_pages
            
        except Exception as e:
            logger.error(f"Error searching torrents: {str(e)}")
            return [], 0, 0

    def _build_magnet_link(self, info_hash: str, name: str) -> str:
        """Build a magnet link with common trackers"""
        trackers = [
            "udp://tracker.coppersurfer.tk:6969/announce",
            "udp://9.rarbg.to:2920/announce",
            "udp://tracker.opentrackr.org:1337",
            "udp://tracker.internetwarriors.net:1337/announce",
            "udp://tracker.leechers-paradise.org:6969/announce",
            "udp://tracker.pirateparty.gr:6969/announce",
            "udp://tracker.cyberia.is:6969/announce"
        ]
        
        tracker_params = "&".join(f"tr={quote(tracker)}" for tracker in trackers)
        return f"magnet:?xt=urn:btih:{info_hash}&dn={quote(name)}&{tracker_params}"

    def _format_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def get_api_status(self) -> dict:
        """Get the health status of The Pirate Bay API"""
        try:
            # First check the health endpoint
            health_response = requests.get('https://apibay.org/health', timeout=5)
            if health_response.status_code != 200:
                return {'The Pirate Bay': False}
                
            # Then check the search endpoint with a test query
            search_url = f"{self.base_url}/q.php"
            params = {
                'q': 'test',
                'cat': '0',
                'page': '1',
                'limit': '1'
            }
            
            search_response = self.session.get(search_url, params=params, timeout=5)
            search_response.raise_for_status()
            
            # Check if we got a valid JSON response
            data = search_response.json()
            if not isinstance(data, list):
                return {'The Pirate Bay': False}
                
            return {'The Pirate Bay': True}
            
        except Exception as e:
            logger.error(f"Error checking API health: {e}")
            return {'The Pirate Bay': False}

# Commented out other API implementations
"""
    async def _search_1337x(self, query: str, category: Optional[str] = None) -> List[SearchResult]:
        # Implementation commented out
        pass

    async def _search_yts(self, query: str) -> List[SearchResult]:
        # Implementation commented out
        pass

    async def _search_nyaa(self, query: str) -> List[SearchResult]:
        # Implementation commented out
        pass

    async def _search_animetosho(self, query: str) -> List[SearchResult]:
        # Implementation commented out
        pass
""" 