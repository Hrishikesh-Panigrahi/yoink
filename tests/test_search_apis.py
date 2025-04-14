"""Tests for YTS and Pirate Bay search APIs."""

import pytest
import responses
from datetime import datetime
from urllib.parse import urlencode, quote

from src.utils.yts_api import YTSAPI, YTSTorrent
from src.utils.pirate_bay import PirateBayAPI, PirateBayTorrent

# Sample responses
YTS_SAMPLE_RESPONSE = {
    "status": "ok",
    "data": {
        "movie_count": 1,
        "movies": [{
            "title": "Test Movie",
            "year": 2024,
            "rating": 8.5,
            "torrents": [{
                "hash": "1234567890abcdef1234",
                "quality": "1080p",
                "seeds": 100,
                "peers": 50,
                "size": "2.1 GB"
            }]
        }]
    }
}

PIRATE_BAY_SAMPLE_RESPONSE = [{
    "id": "1",
    "info_hash": "1234567890abcdef1234",
    "name": "Test Movie",
    "size": "2147483648",  # 2GB in bytes
    "seeders": "100",
    "leechers": "50",
    "added": str(int(datetime.now().timestamp()))
}]

@pytest.fixture
def yts_api():
    """YTS API fixture."""
    return YTSAPI()

@pytest.fixture
def pirate_bay_api():
    """Pirate Bay API fixture."""
    return PirateBayAPI()

class TestYTSAPI:
    """Test cases for YTS API."""
    
    @responses.activate
    def test_successful_search(self, yts_api):
        """Test successful movie search."""
        # Setup mock response
        query = "test movie"
        url = f"{YTSAPI.BASE_URL}/list_movies.json"
        params = {
            "query_term": quote(query),
            "limit": 20,
            "sort_by": "download_count",
            "order_by": "desc",
            "with_rt_ratings": True
        }
        responses.add(
            responses.GET,
            f"{url}?{urlencode(params)}",
            json=YTS_SAMPLE_RESPONSE,
            status=200
        )
        
        # Perform search
        results = yts_api.search_movies(query)
        
        # Verify results
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, YTSTorrent)
        assert "Test Movie" in result.title
        assert result.year == 2024
        assert result.rating == 8.5
        assert result.seeds == 100
        assert result.peers == 50
        assert result.quality == "1080p"
        assert result.size == "2.1 GB"
        assert result.source == "YTS"
        assert result.magnet_url.startswith("magnet:?xt=urn:btih:")
    
    @responses.activate
    def test_empty_response(self, yts_api):
        """Test empty search results."""
        # Setup mock response
        responses.add(
            responses.GET,
            f"{YTSAPI.BASE_URL}/list_movies.json",
            json={"status": "ok", "data": {"movie_count": 0, "movies": []}},
            status=200
        )
        
        results = yts_api.search_movies("nonexistent movie")
        assert len(results) == 0
    
    @responses.activate
    def test_error_response(self, yts_api):
        """Test error handling."""
        # Setup mock response
        responses.add(
            responses.GET,
            f"{YTSAPI.BASE_URL}/list_movies.json",
            json={"status": "error", "status_message": "Query error"},
            status=200
        )
        
        results = yts_api.search_movies("test")
        assert len(results) == 0
    
    @responses.activate
    def test_network_error(self, yts_api):
        """Test network error handling."""
        # Setup mock response
        responses.add(
            responses.GET,
            f"{YTSAPI.BASE_URL}/list_movies.json",
            body=Exception("Network error")
        )
        
        results = yts_api.search_movies("test")
        assert len(results) == 0

class TestPirateBayAPI:
    """Test cases for Pirate Bay API."""
    
    @responses.activate
    def test_successful_search(self, pirate_bay_api):
        """Test successful torrent search."""
        # Setup mock response
        query = "test movie"
        url = f"{PirateBayAPI.BASE_URL}/q.php"
        params = {
            'q': query,
            'cat': '0',
            'page': '1',
            'limit': '20'
        }
        responses.add(
            responses.GET,
            f"{url}?{urlencode(params)}",
            json=PIRATE_BAY_SAMPLE_RESPONSE,
            status=200
        )
        
        # Perform search
        results = pirate_bay_api.search(query)
        
        # Verify results
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, PirateBayTorrent)
        assert result.title == "Test Movie"
        assert result.seeds == 100
        assert result.peers == 50
        assert result.size == "2.0 GB"
        assert result.source == "The Pirate Bay"
        assert result.magnet_url.startswith("magnet:?xt=urn:btih:")
    
    @responses.activate
    def test_empty_response(self, pirate_bay_api):
        """Test empty search results."""
        # Setup mock response
        responses.add(
            responses.GET,
            f"{PirateBayAPI.BASE_URL}/q.php",
            json=[],
            status=200
        )
        
        results = pirate_bay_api.search("nonexistent torrent")
        assert len(results) == 0
    
    @responses.activate
    def test_invalid_response(self, pirate_bay_api):
        """Test invalid response handling."""
        # Setup mock response
        responses.add(
            responses.GET,
            f"{PirateBayAPI.BASE_URL}/q.php",
            json={"error": "Invalid response"},
            status=200
        )
        
        results = pirate_bay_api.search("test")
        assert len(results) == 0
    
    @responses.activate
    def test_network_error(self, pirate_bay_api):
        """Test network error handling."""
        # Setup mock response
        responses.add(
            responses.GET,
            f"{PirateBayAPI.BASE_URL}/q.php",
            body=Exception("Network error")
        )
        
        results = pirate_bay_api.search("test")
        assert len(results) == 0
    
    def test_rate_limiting(self, pirate_bay_api):
        """Test rate limiting functionality."""
        import time
        
        start_time = time.time()
        pirate_bay_api._rate_limit()
        pirate_bay_api._rate_limit()
        end_time = time.time()
        
        # Should take at least 1 second due to rate limiting
        assert end_time - start_time >= 1.0 