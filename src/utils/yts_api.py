"""YTS API integration for movie torrents."""

import logging
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import quote

from src.utils.logger import setup_logger

logger = setup_logger('yts_api')

@dataclass
class YTSTorrent:
    """Represents a YTS torrent result."""
    title: str
    year: int
    rating: float
    seeds: int
    peers: int
    size: str
    quality: str
    magnet_url: str
    source: str = "YTS"

class YTSAPI:
    """Handles interaction with YTS API."""
    
    BASE_URL = "https://yts.mx/api/v2"
    TRACKERS = [
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.openbittorrent.com:80",
        "udp://tracker.coppersurfer.tk:6969",
        "udp://glotorrents.pw:6969/announce",
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://torrent.gresille.org:80/announce",
        "udp://p4p.arenabg.com:1337",
        "udp://tracker.leechers-paradise.org:6969"
    ]
    
    def __init__(self):
        """Initialize YTS API client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
    
    def _build_magnet_url(self, hash: str, title: str) -> str:
        """Build magnet URL with trackers."""
        trackers = "&".join(f"tr={quote(tracker)}" for tracker in self.TRACKERS)
        return f"magnet:?xt=urn:btih:{hash}&dn={quote(title)}&{trackers}"
    
    def search_movies(self, query: str, limit: int = 20) -> List[YTSTorrent]:
        """Search for movies on YTS.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of YTSTorrent objects
        """
        try:
            # Encode query for URL
            encoded_query = quote(query)
            
            # Build request URL and params
            url = f"{self.BASE_URL}/list_movies.json"
            params = {
                "query_term": encoded_query,
                "limit": limit,
                "sort_by": "download_count",
                "order_by": "desc",
                "with_rt_ratings": True
            }
            
            logger.info(f"Searching YTS with URL: {url} and params: {params}")
            
            # Make API request
            response = self.session.get(
                url,
                params=params,
                timeout=10,
                verify=True
            )
            
            # Log response status and headers
            logger.info(f"YTS API response status: {response.status_code}")
            logger.info(f"YTS API response headers: {response.headers}")
            
            response.raise_for_status()
            data = response.json()
            
            # Log response data structure
            logger.info(f"YTS API response data keys: {data.keys()}")
            
            if data.get("status") != "ok":
                logger.error(f"YTS API error: {data.get('status_message')}")
                return []
            
            movie_data = data.get("data", {})
            logger.info(f"YTS API movie data keys: {movie_data.keys()}")
            
            movies = movie_data.get("movies", [])
            movie_count = movie_data.get("movie_count", 0)
            logger.info(f"Found {movie_count} movies in YTS response")
            
            if not movies:
                logger.info("No movies found in YTS response")
                return []
            
            results = []
            for movie in movies:
                try:
                    # Get all available torrents
                    torrents = movie.get("torrents", [])
                    if not torrents:
                        logger.debug(f"No torrents found for movie: {movie.get('title')}")
                        continue
                    
                    # Sort by seeds
                    torrents.sort(key=lambda x: int(x.get("seeds", 0)), reverse=True)
                    
                    # Create a torrent object for each quality
                    for torrent in torrents:
                        try:
                            magnet_url = self._build_magnet_url(
                                torrent.get("hash"),
                                f"{movie['title']} {torrent.get('quality')}"
                            )
                            
                            result = YTSTorrent(
                                title=f"{movie['title']} ({movie['year']}) [{torrent.get('quality')}]",
                                year=int(movie['year']),
                                rating=float(movie.get("rating", 0)),
                                seeds=int(torrent.get("seeds", 0)),
                                peers=int(torrent.get("peers", 0)),
                                size=torrent.get("size", "Unknown"),
                                quality=torrent.get("quality", "Unknown"),
                                magnet_url=magnet_url
                            )
                            results.append(result)
                            logger.debug(f"Added YTS result: {result.title}")
                        except Exception as e:
                            logger.error(f"Error creating torrent object: {str(e)}")
                            continue
                except Exception as e:
                    logger.error(f"Error processing movie {movie.get('title')}: {str(e)}")
                    continue
            
            logger.info(f"Returning {len(results)} YTS results")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"YTS API request failed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error searching YTS: {str(e)}")
            return [] 