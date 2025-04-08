import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import logging
from datetime import datetime
from .logger import setup_logger
from urllib.parse import quote
from functools import lru_cache

# Set up logger
logger = setup_logger('search')

@dataclass
class SearchResult:
    """Data class to store search result information"""
    title: str
    size: str
    seeds: int
    leeches: int
    upload_date: str
    magnet_link: str
    source: str
    category: str = "All"
    verified: bool = False

class SearchUtil:
    """Utility class for searching torrents using The Pirate Bay API"""
    
    def __init__(self):
        self.base_url = "https://apibay.org"
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum time between requests in seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    @lru_cache(maxsize=100)
    def search_torrents(self, query: str, page: int = 1) -> Tuple[List[SearchResult], int, int]:
        """Search for torrents with caching"""
        if not query.strip():
            return [], 0, 0
            
        try:
            self._rate_limit()
            
            # Search endpoint - using the correct endpoint and parameters
            search_url = f"{self.base_url}/q.php"
            params = {
                'q': query,
                'cat': '0',  # All categories
                'page': str(page),
                'limit': '30'
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.error(f"Invalid response format: {data}")
                return [], 0, 0
                
            results = []
            for item in data:
                try:
                    # Skip if no info hash
                    if 'info_hash' not in item:
                        continue
                        
                    magnet = self._build_magnet_link(item['info_hash'], item['name'])
                    result = SearchResult(
                        title=item['name'],
                        size=self._format_size(int(item['size'])),
                        seeds=int(item['seeders']),
                        leeches=int(item['leechers']),
                        upload_date=datetime.fromtimestamp(int(item['added'])).strftime('%Y-%m-%d %H:%M:%S'),
                        source="The Pirate Bay",
                        magnet_link=magnet
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error parsing search result: {e}")
                    continue
                    
            # Estimate total results and pages
            total_results = len(data) * 10  # Rough estimate
            total_pages = (total_results + 29) // 30  # Ceiling division
            
            return results, total_results, total_pages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return [], 0, 0
        except Exception as e:
            logger.error(f"Search error: {e}")
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