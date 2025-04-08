import requests
from typing import List, Dict, Tuple, Optional, Any
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
from .loader import Loader, LoaderStyle
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import asyncio
from datetime import datetime, timedelta

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
    category: str
    verified: bool = False

@dataclass
class APIStatus:
    name: str
    is_healthy: bool
    last_check: float
    error_message: str = ""

class RateLimiter:
    """Rate limiter for API requests"""
    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.last_call_time = datetime.min
        self._lock = threading.Lock()
        
    async def acquire(self):
        """Acquire permission to make an API call"""
        with self._lock:
            now = datetime.now()
            time_since_last_call = (now - self.last_call_time).total_seconds()
            if time_since_last_call < 1.0 / self.calls_per_second:
                await asyncio.sleep(1.0 / self.calls_per_second - time_since_last_call)
            self.last_call_time = datetime.now()

class SearchUtil:
    """Utility class for searching torrents across multiple APIs"""
    
    def __init__(self):
        self.session = None
        self.rate_limiter = RateLimiter()
        self.loader = Loader()
        self._api_health = {}
        self._health_check_lock = threading.Lock()
        self.api_status = {
            '1337x': APIStatus('1337x', True, 0),
            'yts': APIStatus('YTS', True, 0),
            'nyaa': APIStatus('Nyaa', True, 0),
            'animetosho': APIStatus('AnimeTosho', True, 0)
        }
        # Initialize session in constructor
        self._init_session()
        
    def _init_session(self):
        """Initialize the aiohttp session"""
        try:
            # Create a new event loop in the main thread
            if not asyncio._get_running_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            else:
                loop = asyncio.get_event_loop()
                
            # Create session with default headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            self.session = aiohttp.ClientSession(headers=headers)
            
            # Run initial health check
            loop.run_until_complete(self.check_api_health())
        except Exception as e:
            logger.error(f"Failed to initialize session: {str(e)}")
            
    def search_torrents(self, query: str, category: Optional[str] = None, on_progress=None, on_complete=None) -> List[SearchResult]:
        """Synchronous wrapper for async search method"""
        if not query.strip():
            logger.warning("Empty search query")
            return []
            
        try:
            # Create new event loop for this search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Set up progress callback
            if on_progress:
                def progress_callback(msg, progress=None):
                    try:
                        on_progress(msg)
                    except Exception as e:
                        logger.error(f"Progress callback error: {str(e)}")
                self.loader.on_update = progress_callback
                
            # Run search
            results = loop.run_until_complete(self._run_search(query, category))
            
            # Call completion callback
            if on_complete:
                try:
                    on_complete(results)
                except Exception as e:
                    logger.error(f"Complete callback error: {str(e)}")
                    
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
            
        finally:
            try:
                loop.close()
            except Exception:
                pass
                
    async def _run_search(self, query: str, category: Optional[str] = None) -> List[SearchResult]:
        """Internal method to run the search"""
        try:
            # Ensure session is active
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
                
            # Start loader
            self.loader.start(f"Searching for '{query}'...", LoaderStyle.SPINNER)
            
            # Check API health
            health_status = await self.check_api_health()
            healthy_apis = [api for api, healthy in health_status.items() if healthy]
            
            if not healthy_apis:
                logger.warning("No healthy APIs available")
                return []
                
            # Create search tasks
            tasks = []
            for api in healthy_apis:
                if api == '1337x':
                    tasks.append(self._search_1337x(query, category))
                elif api == 'yts':
                    tasks.append(self._search_yts(query))
                elif api == 'nyaa':
                    tasks.append(self._search_nyaa(query))
                elif api == 'animetosho':
                    tasks.append(self._search_animetosho(query))
                    
            # Run searches in parallel with timeout
            results = []
            timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for task in asyncio.as_completed(tasks):
                    try:
                        api_results = await task
                        results.extend(api_results)
                        self.loader.update(
                            f"Found {len(results)} results...",
                            int(len(results) / len(healthy_apis) * 100)
                        )
                    except asyncio.TimeoutError:
                        logger.error("Search timeout")
                    except Exception as e:
                        logger.error(f"Search task error: {str(e)}")
                        
            # Sort results by seeds
            results.sort(key=lambda x: x.seeds, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
            
        finally:
            self.loader.stop()
            
    async def check_api_health(self) -> Dict[str, bool]:
        """Check the health of all APIs"""
        with self._health_check_lock:
            apis = {
                '1337x': 'https://1337x.to',
                'yts': 'https://yts.mx/api/v2/list_movies.json',
                'nyaa': 'https://nyaa.si',
                'animetosho': 'https://animetosho.org'
            }
            
            for name, url in apis.items():
                try:
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url) as response:
                            is_healthy = response.status == 200
                            self._api_health[name] = is_healthy
                            self.api_status[name].is_healthy = is_healthy
                            self.api_status[name].last_check = time.time()
                            logger.info(f"API {name} health check: {'healthy' if is_healthy else 'unhealthy'}")
                except Exception as e:
                    logger.error(f"Health check failed for {name}: {str(e)}")
                    self._api_health[name] = False
                    self.api_status[name].is_healthy = False
                    self.api_status[name].error_message = str(e)
                    self.api_status[name].last_check = time.time()
                    
            return self._api_health.copy()
            
    async def _search_1337x(self, query: str, category: Optional[str] = None) -> List[SearchResult]:
        """Search 1337x API"""
        await self.rate_limiter.acquire()
        
        try:
            url = f"https://1337x.to/search/{query}/1/"
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"1337x API returned status {response.status}")
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                results = []
                for row in soup.select('table.table-list tbody tr'):
                    try:
                        title = row.select_one('td.name').text.strip()
                        size = row.select_one('td.size').text.strip()
                        seeds = int(row.select_one('td.seeds').text.strip())
                        leeches = int(row.select_one('td.leeches').text.strip())
                        date = row.select_one('td.date').text.strip()
                        magnet = row.select_one('td.name a[href^="magnet:"]')['href']
                        
                        results.append(SearchResult(
                            title=title,
                            size=size,
                            seeds=seeds,
                            leeches=leeches,
                            upload_date=date,
                            magnet_link=magnet,
                            source='1337x',
                            category=category or 'general',
                            verified='VIP' in row.select_one('td.name').text
                        ))
                    except Exception as e:
                        logger.error(f"Failed to parse 1337x result: {str(e)}")
                        continue
                        
                return results
                
        except Exception as e:
            logger.error(f"1337x search failed: {str(e)}")
            return []
            
    async def _search_yts(self, query: str) -> List[SearchResult]:
        """Search YTS API for movies"""
        await self.rate_limiter.acquire()
        
        try:
            url = "https://yts.mx/api/v2/list_movies.json"
            params = {
                'query_term': query,
                'sort_by': 'seeds',
                'order_by': 'desc',
                'limit': 50
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"YTS API returned status {response.status}")
                    
                data = await response.json()
                if data.get('status') != 'ok':
                    raise Exception("YTS API returned error status")
                    
                results = []
                movies = data.get('data', {}).get('movies', [])
                
                for movie in movies:
                    try:
                        # Get the best quality torrent
                        torrents = movie.get('torrents', [])
                        if not torrents:
                            continue
                            
                        # Sort by seeds and quality
                        best_torrent = max(torrents, key=lambda x: (x.get('seeds', 0), x.get('quality', '')))
                        
                        title = f"{movie.get('title', '')} ({movie.get('year', '')}) - {best_torrent.get('quality', '')}"
                        size = best_torrent.get('size', '0 MB')
                        seeds = int(best_torrent.get('seeds', 0))
                        leeches = int(best_torrent.get('peers', 0))
                        date = movie.get('date_uploaded', '')
                        magnet = best_torrent.get('url', '')
                        
                        results.append(SearchResult(
                            title=title,
                            size=size,
                            seeds=seeds,
                            leeches=leeches,
                            upload_date=date,
                            magnet_link=magnet,
                            source='YTS',
                            category='movies',
                            verified=True  # YTS is a trusted source
                        ))
                    except Exception as e:
                        logger.error(f"Failed to parse YTS result: {str(e)}")
                        continue
                        
                return results
                
        except Exception as e:
            logger.error(f"YTS search failed: {str(e)}")
            return []
            
    async def _search_nyaa(self, query: str) -> List[SearchResult]:
        """Search Nyaa API for anime torrents"""
        await self.rate_limiter.acquire()
        
        try:
            url = f"https://nyaa.si/?f=0&c=0_0&q={query}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Nyaa API returned status {response.status}")
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                results = []
                for row in soup.select('table.torrent-list tbody tr'):
                    try:
                        title = row.select_one('td:nth-child(2) a').text.strip()
                        size = row.select_one('td:nth-child(4)').text.strip()
                        seeds = int(row.select_one('td:nth-child(6)').text.strip())
                        leeches = int(row.select_one('td:nth-child(7)').text.strip())
                        date = row.select_one('td:nth-child(5)').text.strip()
                        magnet = row.select_one('td:nth-child(3) a[href^="magnet:"]')['href']
                        
                        # Get category from the first column
                        category_cell = row.select_one('td:nth-child(1) a')
                        category = category_cell['title'] if category_cell else 'anime'
                        
                        results.append(SearchResult(
                            title=title,
                            size=size,
                            seeds=seeds,
                            leeches=leeches,
                            upload_date=date,
                            magnet_link=magnet,
                            source='Nyaa',
                            category=category,
                            verified='trusted' in row.get('class', [])
                        ))
                    except Exception as e:
                        logger.error(f"Failed to parse Nyaa result: {str(e)}")
                        continue
                        
                return results
                
        except Exception as e:
            logger.error(f"Nyaa search failed: {str(e)}")
            return []
            
    async def _search_animetosho(self, query: str) -> List[SearchResult]:
        """Search AnimeTosho API for anime torrents"""
        await self.rate_limiter.acquire()
        
        try:
            url = f"https://animetosho.org/search?q={quote(query)}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"AnimeTosho API returned status {response.status}")
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                results = []
                entries = soup.select('div.home_list_entry')
                if not entries:
                    logger.warning("No entries found in AnimeTosho response")
                    return results
                    
                for entry in entries:
                    try:
                        link_div = entry.select_one('div.link')
                        if not link_div or not link_div.select_one('a'):
                            continue
                            
                        title = link_div.select_one('a').text.strip()
                        
                        size_div = entry.select_one('div.size')
                        size = size_div.text.strip() if size_div else "Unknown"
                        
                        stats_div = entry.select_one('div.stats')
                        seeds = 0
                        leeches = 0
                        if stats_div:
                            seeds_span = stats_div.select_one('span.stats_seeds')
                            leeches_span = stats_div.select_one('span.stats_peers')
                            seeds = int(seeds_span.text.strip()) if seeds_span else 0
                            leeches = int(leeches_span.text.strip()) if leeches_span else 0
                            
                        date_div = entry.select_one('div.date')
                        date = date_div.text.strip() if date_div else ""
                        
                        magnet_link = None
                        magnet_a = entry.select_one('a[href^="magnet:"]')
                        if magnet_a:
                            magnet_link = magnet_a['href']
                        else:
                            continue
                            
                        tags = entry.select('div.tags a')
                        category = tags[0].text.strip() if tags else 'anime'
                        
                        results.append(SearchResult(
                            title=title,
                            size=size,
                            seeds=seeds,
                            leeches=leeches,
                            upload_date=date,
                            magnet_link=magnet_link,
                            source='AnimeTosho',
                            category=category,
                            verified='trusted' in entry.get('class', [])
                        ))
                    except Exception as e:
                        logger.error(f"Failed to parse AnimeTosho result: {str(e)}")
                        continue
                        
                return results
                
        except Exception as e:
            logger.error(f"AnimeTosho search failed: {str(e)}")
            return []

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB" 