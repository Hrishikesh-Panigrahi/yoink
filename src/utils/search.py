import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import logging
from datetime import datetime
from .logger import setup_logger

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

    def search_torrents(self, query: str, page: int = 0, category: Optional[str] = None) -> Tuple[List[SearchResult], int, int]:
        """
        Search for torrents using The Pirate Bay API
        Returns: (results, total_results, total_pages)
        """
        if not query.strip():
            logger.warning("Empty search query")
            return [], 0, 0
            
        try:
            self._wait_for_rate_limit()
            
            # Using a reliable Pirate Bay API endpoint
            base_url = "https://apibay.org"
            search_url = f"{base_url}/q.php"
            
            params = {
                'q': query,
                'cat': '0',  # All categories
                'page': str(page),
                'limit': str(self.items_per_page)
            }
            
            logger.info(f"Searching for: {query} (page {page + 1})")
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data or data == []:
                logger.warning(f"No results found for query: {query}")
                return [], 0, 0
                
            # Get total results from the first request
            total_url = f"{base_url}/count"
            total_params = {'q': query}
            total_response = self.session.get(total_url, params=total_params, timeout=10)
            total_response.raise_for_status()
            total_data = total_response.json()
            
            total_results = int(total_data.get('total', 0))
            total_pages = (total_results + self.items_per_page - 1) // self.items_per_page
            
            results = []
            for item in data:
                try:
                    # Skip if item is not a valid torrent
                    if not isinstance(item, dict) or 'name' not in item:
                        continue
                        
                    # Convert size from bytes to human readable format
                    size_bytes = int(item.get('size', 0))
                    size_str = self._format_size(size_bytes)
                    
                    result = SearchResult(
                        title=item.get('name', 'Unknown'),
                        size=size_str,
                        seeds=int(item.get('seeders', 0)),
                        leeches=int(item.get('leechers', 0)),
                        upload_date=datetime.fromtimestamp(int(item.get('added', 0))).strftime('%Y-%m-%d %H:%M:%S'),
                        magnet_link=f"magnet:?xt=urn:btih:{item.get('info_hash', '')}&dn={item.get('name', 'Unknown')}",
                        source='The Pirate Bay',
                        category=item.get('category', 'All'),
                        verified=item.get('status', '') == 'vip'
                    )
                    results.append(result)
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing torrent result: {e}")
                    continue
            
            # Sort results by seeds
            results.sort(key=lambda x: x.seeds, reverse=True)
            logger.info(f"Found {len(results)} results for query: {query} (page {page + 1} of {total_pages})")
            return results, total_results, total_pages
            
        except requests.RequestException as e:
            logger.error(f"Error searching torrents: {e}")
            return [], 0, 0
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return [], 0, 0

    def _format_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

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