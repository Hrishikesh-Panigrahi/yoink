"""Pirate Bay API integration."""

import logging
import requests
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from src.utils.logger import setup_logger

logger = setup_logger('pirate_bay')

@dataclass
class PirateBayTorrent:
    """Represents a Pirate Bay torrent result."""
    title: str
    size: str
    seeds: int
    peers: int
    date: str
    magnet_url: str
    source: str = "The Pirate Bay"
    quality: Optional[str] = None
    year: Optional[int] = None
    rating: Optional[float] = None

class PirateBayAPI:
    """Handles interaction with Pirate Bay API."""
    
    BASE_URL = "https://apibay.org"
    
    def __init__(self):
        """Initialize Pirate Bay API client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum time between requests in seconds
    
    def _rate_limit(self):
        """Implement rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()
    
    def _format_size(self, bytes: int) -> str:
        """Format size in human-readable format."""
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 * 1024:
            return f"{bytes/1024:.1f} KB"
        elif bytes < 1024 * 1024 * 1024:
            return f"{bytes/(1024*1024):.1f} MB"
        else:
            return f"{bytes/(1024*1024*1024):.1f} GB"
    
    def _build_magnet_link(self, info_hash: str, name: str) -> str:
        """Build magnet link from info hash and name."""
        encoded_name = quote(name)
        return f"magnet:?xt=urn:btih:{info_hash}&dn={encoded_name}"
    
    def search(self, query: str, page: int = 1, limit: int = 20) -> List[PirateBayTorrent]:
        """Search for torrents on Pirate Bay.
        
        Args:
            query: Search query
            page: Page number (1-based)
            limit: Results per page
            
        Returns:
            List of PirateBayTorrent objects
        """
        try:
            self._rate_limit()
            
            # Search endpoint
            search_url = f"{self.BASE_URL}/q.php"
            params = {
                'q': query,
                'cat': '0',  # All categories
                'page': str(page),
                'limit': str(limit)
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.error(f"Invalid response format: {data}")
                return []
            
            results = []
            for item in data:
                try:
                    # Skip if no info hash
                    if 'info_hash' not in item:
                        continue
                    
                    magnet = self._build_magnet_link(item['info_hash'], item['name'])
                    torrent = PirateBayTorrent(
                        title=item['name'],
                        size=self._format_size(int(item['size'])),
                        seeds=int(item['seeders']),
                        peers=int(item['leechers']),
                        date=datetime.fromtimestamp(int(item['added'])).strftime('%Y-%m-%d'),
                        magnet_url=magnet
                    )
                    results.append(torrent)
                except Exception as e:
                    logger.error(f"Error parsing search result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Pirate Bay: {str(e)}")
            return [] 