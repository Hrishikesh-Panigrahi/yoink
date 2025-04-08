import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import logging
from datetime import datetime
from .logger import setup_logger
from urllib.parse import quote

# Set up logger
logger = setup_logger('search_util')

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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum seconds between requests
        self.items_per_page = 30  # Reduced items per page for better usability

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    def search_torrents(self, query: str, page: int = 1) -> Tuple[List[SearchResult], int, int]:
        """Search for torrents using The Pirate Bay API"""
        try:
            # Encode query for URL
            encoded_query = quote(query)
            
            # Make request to search endpoint
            response = requests.get(f'https://apibay.org/q.php?q={encoded_query}&cat=0')
            response.raise_for_status()
            
            # Parse results
            results = response.json()
            if not results or (isinstance(results, list) and len(results) == 1 and results[0].get('name') == 'No results returned'):
                logger.info(f"No results found for query: {query}")
                return [], 0, 0
                
            # Calculate pagination
            items_per_page = 30
            total_results = len(results)
            total_pages = (total_results + items_per_page - 1) // items_per_page
            
            # Get results for current page
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_results)
            page_results = results[start_idx:end_idx]
            
            # Convert to SearchResult objects
            search_results = []
            for result in page_results:
                try:
                    # Build magnet link
                    info_hash = result.get('info_hash', '')
                    name = result.get('name', '')
                    magnet = self._build_magnet_link(info_hash, name)
                    
                    # Create search result
                    search_results.append(SearchResult(
                        title=name,
                        size=self._format_size(int(result.get('size', 0))),
                        seeds=int(result.get('seeders', 0)),
                        leeches=int(result.get('leechers', 0)),
                        upload_date=datetime.fromtimestamp(int(result.get('added', 0))).strftime('%Y-%m-%d %H:%M:%S'),
                        magnet_link=magnet,
                        source="The Pirate Bay"
                    ))
                except Exception as e:
                    logger.error(f"Error parsing result: {e}")
                    continue
            
            logger.info(f"Found {total_results} results for query: {query} (page {page} of {total_pages})")
            return search_results, total_results, total_pages
            
        except Exception as e:
            logger.error(f"Error searching torrents: {e}")
            raise

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
            response = requests.get('https://apibay.org/health', timeout=10)
            return {'The Pirate Bay': response.status_code == 200}
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