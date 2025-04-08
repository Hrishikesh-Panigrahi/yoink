import requests
from typing import List, Dict, Tuple
import json
from dataclasses import dataclass
import time
from urllib.parse import quote, urljoin
import logging
from requests.exceptions import RequestException
from .logger import setup_logger
import threading
import re

# Set up logger
logger = setup_logger('search_util')

@dataclass
class SearchResult:
    name: str
    size: int
    seeds: int
    peers: int
    magnet_link: str
    source: str

@dataclass
class APIStatus:
    name: str
    is_healthy: bool
    last_check: float
    error_message: str = ""

class SearchUtil:
    def __init__(self):
        logger.info("Initializing SearchUtil")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # API endpoints
        self.apis = {
            '1337x': 'https://apibay.org/api.php',  # 1337x API
            'nyaa': 'https://nyaa.si/api/search',
            'anime': 'https://animetosho.org/api/search',
            'torlock': 'https://www.torlock.com/api/search'
        }
        
        # API health status
        self.api_status = {
            '1337x': APIStatus('1337x', True, 0),  # Start as healthy
            'nyaa': APIStatus('Nyaa', True, 0),  # Start as healthy
            'anime': APIStatus('AnimeTosho', True, 0),  # Start as healthy
            'torlock': APIStatus('TorLock', True, 0)  # Start as healthy
        }
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # seconds
        self.health_check_interval = 60.0  # seconds
        
        # Start background health check
        self._start_background_health_check()
        
        logger.debug(f"SearchUtil initialized with {len(self.apis)} API endpoints")
        
    def _start_background_health_check(self):
        """Start background thread for API health checks"""
        def health_check_worker():
            while True:
                for api_name in self.apis.keys():
                    try:
                        self._check_single_api_health(api_name)
                    except Exception as e:
                        logger.error(f"Error checking {api_name} health: {str(e)}")
                time.sleep(self.health_check_interval)

        health_check_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_check_thread.start()
        logger.info("Started background API health check thread")

    def _check_single_api_health(self, api_name: str):
        """Check health of a single API endpoint"""
        current_time = time.time()
        status = self.api_status[api_name]
        
        # Only check health if enough time has passed since last check
        if current_time - status.last_check < self.health_check_interval:
            return status.is_healthy
            
        try:
            logger.debug(f"Checking health of {api_name} API")
            if api_name == '1337x':
                response = self.session.get(f"{self.apis[api_name]}?info_hash=test", timeout=5)
            elif api_name == 'nyaa':
                response = self.session.get(f"{self.apis[api_name]}?q=test", timeout=5)
            elif api_name == 'anime':
                response = self.session.get(f"{self.apis[api_name]}?q=test", timeout=5)
            elif api_name == 'torlock':
                response = self.session.get(f"{self.apis[api_name]}?q=test", timeout=5)
                
            response.raise_for_status()
            status.is_healthy = True
            status.error_message = ""
            logger.info(f"{api_name} API is healthy")
        except Exception as e:
            status.is_healthy = False
            status.error_message = str(e)
            logger.warning(f"{api_name} API is unhealthy: {str(e)}")
            
        status.last_check = current_time
        return status.is_healthy

    def check_api_health(self, api_name: str) -> bool:
        """Get current health status of an API endpoint"""
        return self.api_status[api_name].is_healthy
        
    def get_healthy_apis(self) -> List[APIStatus]:
        """Get status of all APIs"""
        for api_name in self.apis.keys():
            self.check_api_health(api_name)
        return list(self.api_status.values())
        
    def _rate_limit(self, api_name: str):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        if api_name in self.last_request_time:
            time_since_last = current_time - self.last_request_time[api_name]
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                logger.debug(f"Rate limiting {api_name}: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self.last_request_time[api_name] = time.time()
        
    def _make_request(self, api_name: str, url: str, params: dict) -> dict:
        """Make an API request with error handling"""
        if not self.check_api_health(api_name):
            raise Exception(f"{api_name} API is currently unavailable")
            
        try:
            self._rate_limit(api_name)
            logger.info(f"Making request to {api_name}: {url}")
            logger.debug(f"Request parameters: {params}")
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Received response from {api_name}: {len(str(data))} bytes")
            return data
        except RequestException as e:
            logger.error(f"API request failed for {api_name}: {str(e)}")
            raise
            
    def search_1337x(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search 1337x with pagination"""
        logger.info(f"Searching 1337x for: {query} (page {page})")
        try:
            params = {
                'info_hash': '',
                'name': query,
                'page': page,
                'limit': per_page,
                'category': '0',  # All categories
                'sort': 'seeds',
                'order': 'desc'
            }
            
            response = self.session.get(self.apis['1337x'], params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            total_results = len(data) if isinstance(data, list) else 0
            
            for item in data:
                try:
                    # Convert size from string (e.g., "1.5 GB") to bytes
                    size_str = item.get('size', '0 B')
                    size_bytes = self._parse_size(size_str)
                    
                    results.append(SearchResult(
                        name=item.get('name', ''),
                        size=size_bytes,
                        seeds=int(item.get('seeders', 0)),
                        peers=int(item.get('leechers', 0)),
                        magnet_link=item.get('magnet', ''),
                        source='1337x'
                    ))
                except Exception as e:
                    logger.error(f"Error parsing 1337x result: {str(e)}")
                    continue
                    
            logger.info(f"1337x search returned {len(results)} results (total: {total_results})")
            return results, total_results
        except Exception as e:
            logger.error(f"1337x search error: {str(e)}", exc_info=True)
            return [], 0

    def search_nyaa(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search Nyaa.si with pagination"""
        logger.info(f"Searching Nyaa for: {query} (page {page})")
        try:
            params = {
                'q': query,
                'page': page,
                'limit': per_page,
                'sort': 'seeders',
                'order': 'desc'
            }
            data = self._make_request('nyaa', self.apis['nyaa'], params)
            
            results = []
            total_results = data.get('total', 0)
            
            for item in data.get('items', []):
                results.append(SearchResult(
                    name=item['name'],
                    size=int(item['size']),
                    seeds=int(item.get('seeders', 0)),
                    peers=int(item.get('leechers', 0)),
                    magnet_link=item['magnet'],
                    source='Nyaa'
                ))
            logger.info(f"Nyaa search returned {len(results)} results (total: {total_results})")
            return results, total_results
        except Exception as e:
            logger.error(f"Nyaa search error: {str(e)}", exc_info=True)
            return [], 0
            
    def search_anime(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search AnimeTosho with pagination"""
        logger.info(f"Searching AnimeTosho for: {query} (page {page})")
        try:
            params = {
                'q': query,
                'offset': (page - 1) * per_page,
                'limit': per_page
            }
            data = self._make_request('anime', self.apis['anime'], params)
            
            results = []
            total_results = data.get('total', 0)
            
            for item in data.get('items', []):
                results.append(SearchResult(
                    name=item['title'],
                    size=int(item['size']),
                    seeds=int(item.get('seeds', 0)),
                    peers=int(item.get('peers', 0)),
                    magnet_link=item['magnet'],
                    source='AnimeTosho'
                ))
            logger.info(f"AnimeTosho search returned {len(results)} results (total: {total_results})")
            return results, total_results
        except Exception as e:
            logger.error(f"AnimeTosho search error: {str(e)}", exc_info=True)
            return [], 0
            
    def search_torlock(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search TorLock with pagination"""
        logger.info(f"Searching TorLock for: {query} (page {page})")
        try:
            params = {
                'q': query,
                'page': page,
                'per_page': per_page,
                'orderby': 'seeds',
                'order': 'desc'
            }
            data = self._make_request('torlock', self.apis['torlock'], params)
            
            results = []
            total_results = data.get('total', 0)
            
            for item in data.get('items', []):
                results.append(SearchResult(
                    name=item['name'],
                    size=int(item['size']),
                    seeds=int(item.get('seeds', 0)),
                    peers=int(item.get('peers', 0)),
                    magnet_link=item['magnet'],
                    source='TorLock'
                ))
            logger.info(f"TorLock search returned {len(results)} results (total: {total_results})")
            return results, total_results
        except Exception as e:
            logger.error(f"TorLock search error: {str(e)}", exc_info=True)
            return [], 0
        
    def search_torrents(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """
        Search for torrents across multiple sources with pagination.
        Returns a tuple of (results, total_count)
        """
        logger.info(f"Starting search for query: {query} (page {page})")
        all_results = []
        total_results = 0
        
        # Search all healthy APIs
        sources = [
            ('1337x', self.search_1337x),
            ('nyaa', self.search_nyaa),
            ('anime', self.search_anime),
            ('torlock', self.search_torlock)
        ]
        
        for api_name, search_func in sources:
            if self.check_api_health(api_name):
                try:
                    logger.info(f"Searching {api_name}...")
                    results, total = search_func(query, page, per_page)
                    all_results.extend(results)
                    total_results += total
                except Exception as e:
                    logger.error(f"Error searching {api_name}: {str(e)}", exc_info=True)
                    continue
            else:
                logger.warning(f"Skipping {api_name} as it is unhealthy")
        
        # Sort by seeds and limit results
        all_results.sort(key=lambda x: x.seeds, reverse=True)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        final_results = all_results[start_idx:end_idx]
        
        logger.info(f"Total results found: {len(final_results)} (total across all sources: {total_results})")
        return final_results, total_results
        
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _parse_size(self, size_str: str) -> int:
        """Convert size string to bytes"""
        try:
            parts = size_str.strip().split()
            if len(parts) != 2:
                return 0
                
            value = float(parts[0])
            unit = parts[1].upper()
            
            multipliers = {
                'B': 1,
                'KB': 1024,
                'MB': 1024**2,
                'GB': 1024**3,
                'TB': 1024**4
            }
            
            return int(value * multipliers.get(unit, 1))
        except Exception:
            return 0 