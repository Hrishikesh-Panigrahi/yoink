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
from bs4 import BeautifulSoup
from .loader import Loader

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
        self.logger = setup_logger('search_util')
        self.loader = Loader("Searching torrents...")
        
        # API endpoints
        self.api_urls = {
            '1337x': 'https://1337x.to',
            'YTS': 'https://yts.mx/api/v2',
            'Nyaa': 'https://nyaa.si',
            'AnimeTosho': 'https://animetosho.org'
        }
        
        # API search methods
        self.apis = {
            '1337x': self.search_1337x,
            'YTS': self.search_yts,
            'Nyaa': self.search_nyaa,
            'AnimeTosho': self.search_animetosho
        }
        
        logger.info("Initializing SearchUtil")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # API health status
        self.api_status = {
            '1337x': APIStatus('1337x', True, 0),
            'YTS': APIStatus('YTS', True, 0),
            'Nyaa': APIStatus('Nyaa', True, 0),
            'AnimeTosho': APIStatus('AnimeTosho', True, 0)
        }
        
        # Rate limiting and timeouts
        self.last_request_time = {}
        self.min_request_interval = 2.0  # Increased to avoid rate limiting
        self.health_check_interval = 120.0  # Increased to reduce API load
        self.request_timeout = 20.0  # Increased for slower connections
        
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
                response = self.session.get(self.api_urls[api_name], timeout=self.request_timeout)
            elif api_name == 'YTS':
                response = self.session.get(self.api_urls[api_name], timeout=self.request_timeout)
            elif api_name == 'Nyaa':
                response = self.session.get(self.api_urls[api_name], timeout=self.request_timeout)
            elif api_name == 'AnimeTosho':
                response = self.session.get(self.api_urls[api_name], timeout=self.request_timeout)
                
            response.raise_for_status()
            
            # Additional check for YTS API response format
            if api_name == 'YTS':
                data = response.json()
                if not isinstance(data, dict) or 'status' not in data:
                    raise ValueError("Invalid YTS API response format")
                    
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
        """Make an API request with error handling and retries"""
        if not self.check_api_health(api_name):
            raise Exception(f"{api_name} API is currently unavailable")
            
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                self._rate_limit(api_name)
                logger.info(f"Making request to {api_name}: {url} (attempt {attempt + 1}/{max_retries})")
                logger.debug(f"Request parameters: {params}")
                
                response = self.session.get(url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"Received response from {api_name}: {len(str(data))} bytes")
                return data
            except RequestException as e:
                logger.warning(f"API request failed for {api_name} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                logger.error(f"All retries failed for {api_name}")
                raise
            
    def _parse_size(self, size_str: str) -> int:
        """Convert size string to bytes"""
        try:
            size_str = size_str.lower().strip()
            if not size_str:
                return 0
                
            multipliers = {
                'kb': 1024,
                'mb': 1024 * 1024,
                'gb': 1024 * 1024 * 1024,
                'tb': 1024 * 1024 * 1024 * 1024
            }
            
            for unit, multiplier in multipliers.items():
                if unit in size_str:
                    try:
                        number = float(size_str.replace(unit, '').strip())
                        return int(number * multiplier)
                    except ValueError:
                        return 0
            return 0
        except Exception as e:
            logger.error(f"Error parsing size string '{size_str}': {str(e)}")
            return 0

    def search_torrents(self, query: str, on_progress=None, on_complete=None):
        """Search for torrents across all available APIs"""
        self.logger.info(f"Starting search for: {query}")
        self.loader.start()
        
        all_results = []
        total_results = 0
        api_count = len(self.apis)
        
        try:
            for i, (api_name, search_func) in enumerate(self.apis.items(), 1):
                if on_progress:
                    on_progress(api_name)
                    
                try:
                    results, count = search_func(query)
                    if results:
                        all_results.extend(results)
                        total_results += count
                        self.logger.info(f"Found {len(results)} results from {api_name}")
                except Exception as e:
                    self.logger.error(f"Error searching {api_name}: {str(e)}", exc_info=True)
                    continue
                    
            # Sort results by number of seeds
            if all_results:
                all_results.sort(key=lambda x: x.seeds if hasattr(x, 'seeds') else 0, reverse=True)
            
            if on_complete:
                on_complete(all_results)
                
            return all_results, total_results
            
        finally:
            self.loader.stop()

    def search_1337x(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search 1337x for torrents"""
        self.logger.info(f"Searching 1337x for: {query} (page {page})")
        try:
            search_url = f"{self.api_urls['1337x']}/search/{quote(query)}/{page}/"
            response = self.session.get(search_url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find all torrent rows
            for row in soup.select('tbody tr'):
                try:
                    name_cell = row.select_one('td.name')
                    if not name_cell:
                        continue
                        
                    name = name_cell.select_one('a:nth-of-type(2)').text.strip()
                    size = self._parse_size(row.select_one('td.size').text.strip())
                    seeds = int(row.select_one('td.seeds').text.strip())
                    peers = int(row.select_one('td.leeches').text.strip())
                    
                    # Get the torrent details page URL
                    details_url = urljoin(self.api_urls['1337x'], name_cell.select_one('a:nth-of-type(2)')['href'])
                    
                    # Get magnet link from details page
                    details_response = self.session.get(details_url, timeout=self.request_timeout)
                    details_soup = BeautifulSoup(details_response.text, 'html.parser')
                    magnet_link = details_soup.select_one('a[href^="magnet:"]')['href']
                    
                    results.append(SearchResult(
                        name=name,
                        size=size,
                        seeds=seeds,
                        peers=peers,
                        magnet_link=magnet_link,
                        source='1337x'
                    ))
                    
                    if len(results) >= per_page:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error parsing 1337x result row: {str(e)}")
                    continue
                    
            # Get total results count
            pagination = soup.select_one('div.pagination')
            total_results = len(results)  # Default to current page count
            if pagination:
                try:
                    last_page = max(int(a.text) for a in pagination.select('a') if a.text.isdigit())
                    total_results = last_page * per_page
                except Exception as e:
                    self.logger.error(f"Error parsing 1337x pagination: {str(e)}")
                    
            self.logger.info(f"1337x search returned {len(results)} results (total: {total_results})")
            return results, total_results
            
        except Exception as e:
            self.logger.error(f"1337x search error: {str(e)}", exc_info=True)
            return [], 0

    def search_nyaa(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search Nyaa for torrents"""
        self.logger.info(f"Searching Nyaa for: {query} (page {page})")
        try:
            search_url = f"{self.api_urls['Nyaa']}/?f=0&c=0_0&q={quote(query)}&p={page}"
            response = self.session.get(search_url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find all torrent rows
            for row in soup.select('table.torrent-list tbody tr'):
                try:
                    name = row.select_one('td:nth-child(2) a').text.strip()
                    size = self._parse_size(row.select_one('td:nth-child(4)').text.strip())
                    seeds = int(row.select_one('td:nth-child(6)').text.strip())
                    peers = int(row.select_one('td:nth-child(7)').text.strip())
                    magnet_link = row.select_one('td:nth-child(3) a[href^="magnet:"]')['href']
                    
                    results.append(SearchResult(
                        name=name,
                        size=size,
                        seeds=seeds,
                        peers=peers,
                        magnet_link=magnet_link,
                        source='Nyaa'
                    ))
                    
                    if len(results) >= per_page:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error parsing Nyaa result row: {str(e)}")
                    continue
                    
            # Get total results count
            total_results = len(results)  # Default to current page count
            try:
                pagination = soup.select_one('ul.pagination')
                if pagination:
                    last_page = max(int(a.text) for a in pagination.select('a') if a.text.isdigit())
                    total_results = last_page * per_page
            except Exception as e:
                self.logger.error(f"Error parsing Nyaa pagination: {str(e)}")
                
            self.logger.info(f"Nyaa search returned {len(results)} results (total: {total_results})")
            return results, total_results
            
        except Exception as e:
            self.logger.error(f"Nyaa search error: {str(e)}", exc_info=True)
            return [], 0

    def search_animetosho(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search AnimeTosho for torrents"""
        self.logger.info(f"Searching AnimeTosho for: {query} (page {page})")
        try:
            search_url = f"{self.api_urls['AnimeTosho']}/search?q={quote(query)}&offset={(page-1)*per_page}"
            response = self.session.get(search_url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find all torrent entries
            for entry in soup.select('div.home_list_entry'):
                try:
                    name = entry.select_one('div.link a').text.strip()
                    size_text = entry.select_one('div.size').text.strip()
                    size = self._parse_size(size_text)
                    
                    # Seeds and peers are not always available
                    seeds_text = entry.select_one('span.stats_seeds')
                    peers_text = entry.select_one('span.stats_peers')
                    seeds = int(seeds_text.text) if seeds_text else 0
                    peers = int(peers_text.text) if peers_text else 0
                    
                    magnet_link = entry.select_one('a[href^="magnet:"]')['href']
                    
                    results.append(SearchResult(
                        name=name,
                        size=size,
                        seeds=seeds,
                        peers=peers,
                        magnet_link=magnet_link,
                        source='AnimeTosho'
                    ))
                    
                    if len(results) >= per_page:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error parsing AnimeTosho result: {str(e)}")
                    continue
                    
            # Get total results count from pagination info
            total_results = len(results)  # Default to current page count
            try:
                pagination_text = soup.select_one('div.pager_info')
                if pagination_text:
                    match = re.search(r'of (\d+)', pagination_text.text)
                    if match:
                        total_results = int(match.group(1))
            except Exception as e:
                self.logger.error(f"Error parsing AnimeTosho pagination: {str(e)}")
                
            self.logger.info(f"AnimeTosho search returned {len(results)} results (total: {total_results})")
            return results, total_results
            
        except Exception as e:
            self.logger.error(f"AnimeTosho search error: {str(e)}", exc_info=True)
            return [], 0

    def search_yts(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[SearchResult], int]:
        """Search YTS for torrents"""
        self.logger.info(f"Searching YTS for: {query} (page {page})")
        try:
            params = {
                'query_term': query,
                'page': page,
                'limit': per_page,
                'sort_by': 'seeds',
                'order_by': 'desc'
            }
            
            response = self.session.get(f"{self.api_urls['YTS']}/list_movies.json", params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict) or 'status' not in data or data['status'] != 'ok':
                raise ValueError("Invalid YTS API response")
                
            results = []
            movie_data = data.get('data', {})
            movies = movie_data.get('movies', [])
            total_results = movie_data.get('movie_count', 0)
            
            for movie in movies:
                try:
                    # Get the best quality torrent
                    torrents = sorted(movie.get('torrents', []), 
                                   key=lambda x: self._parse_size(x.get('size', '0')), 
                                   reverse=True)
                    if not torrents:
                        continue
                        
                    best_torrent = torrents[0]
                    name = f"{movie.get('title', '')} ({movie.get('year', '')}) - {best_torrent.get('quality', '')}"
                    size = self._parse_size(best_torrent.get('size', '0'))
                    seeds = int(best_torrent.get('seeds', 0))
                    peers = int(best_torrent.get('peers', 0))
                    
                    # Construct magnet link
                    hash = best_torrent.get('hash', '')
                    if not hash:
                        continue
                        
                    magnet_link = f"magnet:?xt=urn:btih:{hash}&dn={quote(name)}&tr=udp://tracker.openbittorrent.com:80"
                    
                    results.append(SearchResult(
                        name=name,
                        size=size,
                        seeds=seeds,
                        peers=peers,
                        magnet_link=magnet_link,
                        source='YTS'
                    ))
                except Exception as e:
                    self.logger.error(f"Error parsing YTS movie result: {str(e)}")
                    continue
                    
            self.logger.info(f"YTS search returned {len(results)} results (total: {total_results})")
            return results, total_results
            
        except Exception as e:
            self.logger.error(f"YTS search error: {str(e)}", exc_info=True)
            return [], 0

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB" 