import requests
from typing import List, Dict
import json
from dataclasses import dataclass
import time
from urllib.parse import quote
import logging
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    name: str
    size: int
    seeds: int
    peers: int
    magnet_link: str
    source: str

class SearchUtil:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # API endpoints
        self.apis = {
            'yts': 'https://yts.mx/api/v2/list_movies.json',
            'piratebay': 'https://apibay.org/search.php',
            'limetorrents': 'https://api.limetorrents.pro/api/v1/search'
        }
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # seconds
        
    def _rate_limit(self, api_name: str):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        if api_name in self.last_request_time:
            time_since_last = current_time - self.last_request_time[api_name]
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time[api_name] = time.time()
        
    def _make_request(self, api_name: str, url: str, params: dict) -> dict:
        """Make an API request with error handling"""
        try:
            self._rate_limit(api_name)
            logger.info(f"Making request to {api_name}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"API request failed for {api_name}: {str(e)}")
            raise
            
    def search_yts(self, query: str) -> List[SearchResult]:
        """Search YTS (YIFY) for movies"""
        try:
            params = {
                'query_term': query,
                'sort_by': 'seeds',
                'order_by': 'desc',
                'limit': 20
            }
            data = self._make_request('yts', self.apis['yts'], params)
            
            results = []
            for movie in data.get('data', {}).get('movies', []):
                for torrent in movie.get('torrents', []):
                    results.append(SearchResult(
                        name=f"{movie['title']} ({movie['year']}) - {torrent['quality']}",
                        size=int(torrent['size_bytes']),
                        seeds=torrent.get('seeds', 0),
                        peers=torrent.get('peers', 0),
                        magnet_link=torrent['url'],
                        source='YTS'
                    ))
            logger.info(f"YTS search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"YTS search error: {str(e)}")
            return []
            
    def search_piratebay(self, query: str) -> List[SearchResult]:
        """Search The Pirate Bay"""
        try:
            params = {
                'q': query,
                'cat': '0',  # All categories
                'order': 'desc',
                'by': 'seeds'
            }
            data = self._make_request('piratebay', self.apis['piratebay'], params)
            
            results = []
            for item in data:
                results.append(SearchResult(
                    name=item['name'],
                    size=int(item['size']),
                    seeds=int(item['seeders']),
                    peers=int(item['leechers']),
                    magnet_link=f"magnet:?xt=urn:btih:{item['info_hash']}&dn={quote(item['name'])}",
                    source='The Pirate Bay'
                ))
            logger.info(f"PirateBay search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"PirateBay search error: {str(e)}")
            return []
            
    def search_limetorrents(self, query: str) -> List[SearchResult]:
        """Search LimeTorrents"""
        try:
            params = {
                'query': query,
                'limit': 20,
                'sort': 'seeds',
                'order': 'desc'
            }
            data = self._make_request('limetorrents', self.apis['limetorrents'], params)
            
            results = []
            for item in data.get('items', []):
                results.append(SearchResult(
                    name=item['name'],
                    size=int(item['size']),
                    seeds=item.get('seeds', 0),
                    peers=item.get('peers', 0),
                    magnet_link=item['magnet'],
                    source='LimeTorrents'
                ))
            logger.info(f"LimeTorrents search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"LimeTorrents search error: {str(e)}")
            return []
        
    def search_torrents(self, query: str, limit: int = 20) -> List[SearchResult]:
        """
        Search for torrents across multiple sources.
        """
        logger.info(f"Starting search for query: {query}")
        all_results = []
        
        # Search all sources
        sources = [
            ('YTS', self.search_yts),
            ('PirateBay', self.search_piratebay),
            ('LimeTorrents', self.search_limetorrents)
        ]
        
        for source_name, search_func in sources:
            try:
                logger.info(f"Searching {source_name}...")
                results = search_func(query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error searching {source_name}: {str(e)}")
                continue
        
        # Sort by seeds and limit results
        all_results.sort(key=lambda x: x.seeds, reverse=True)
        final_results = all_results[:limit]
        logger.info(f"Total results found: {len(final_results)}")
        return final_results
        
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB" 