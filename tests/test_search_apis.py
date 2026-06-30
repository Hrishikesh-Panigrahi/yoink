"""Tests for the YTS and Pirate Bay provider functions."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

import pytest
import responses

from providers.pirate_bay import PIRATE_BAY_BASE_URL, search_pirate_bay
from providers.yts import YTS_BASE_URL, search_yts

YTS_SAMPLE_RESPONSE = {
    "status": "ok",
    "data": {
        "movie_count": 1,
        "movies": [
            {
                "title": "Test Movie",
                "year": 2024,
                "rating": 8.5,
                "torrents": [
                    {
                        "hash": "1234567890abcdef1234",
                        "quality": "1080p",
                        "seeds": 100,
                        "peers": 50,
                        "size": "2.1 GB",
                    }
                ],
            }
        ],
    },
}

PIRATE_BAY_SAMPLE_RESPONSE = [
    {
        "id": "1",
        "info_hash": "1234567890abcdef1234",
        "name": "Test Movie",
        "size": "2147483648",  # 2 GB in bytes
        "seeders": "100",
        "leechers": "50",
        "added": str(int(datetime.now().timestamp())),
    }
]


class TestYTS:
    @responses.activate
    def test_successful_search(self):
        query = "test movie"
        url = f"{YTS_BASE_URL}/list_movies.json"
        params = {
            "query_term": query,
            "limit": 20,
            "sort_by": "download_count",
            "order_by": "desc",
            "with_rt_ratings": True,
        }
        responses.add(
            responses.GET,
            f"{url}?{urlencode(params)}",
            json=YTS_SAMPLE_RESPONSE,
            status=200,
        )

        results = search_yts(query)

        assert len(results) == 1
        result = results[0]
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
    def test_empty_response(self):
        responses.add(
            responses.GET,
            f"{YTS_BASE_URL}/list_movies.json",
            json={"status": "ok", "data": {"movie_count": 0, "movies": []}},
            status=200,
        )
        assert search_yts("nonexistent movie") == []

    @responses.activate
    def test_error_response(self):
        responses.add(
            responses.GET,
            f"{YTS_BASE_URL}/list_movies.json",
            json={"status": "error", "status_message": "Query error"},
            status=200,
        )
        assert search_yts("test") == []

    @responses.activate
    def test_network_error(self):
        responses.add(
            responses.GET,
            f"{YTS_BASE_URL}/list_movies.json",
            body=Exception("Network error"),
        )
        assert search_yts("test") == []


class TestPirateBay:
    @responses.activate
    def test_successful_search(self):
        query = "test movie"
        url = f"{PIRATE_BAY_BASE_URL}/q.php"
        params = {"q": query, "cat": "0", "page": "1", "limit": "20"}
        responses.add(
            responses.GET,
            f"{url}?{urlencode(params)}",
            json=PIRATE_BAY_SAMPLE_RESPONSE,
            status=200,
        )

        results = search_pirate_bay(query)

        assert len(results) == 1
        result = results[0]
        assert result.title == "Test Movie"
        assert result.seeds == 100
        assert result.peers == 50
        assert result.size == "2.0 GB"
        assert result.source == "The Pirate Bay"
        assert result.magnet_url.startswith("magnet:?xt=urn:btih:")

    @responses.activate
    def test_empty_response(self):
        responses.add(
            responses.GET,
            f"{PIRATE_BAY_BASE_URL}/q.php",
            json=[],
            status=200,
        )
        assert search_pirate_bay("nonexistent torrent") == []

    @responses.activate
    def test_invalid_response(self):
        responses.add(
            responses.GET,
            f"{PIRATE_BAY_BASE_URL}/q.php",
            json={"error": "Invalid response"},
            status=200,
        )
        assert search_pirate_bay("test") == []

    @responses.activate
    def test_network_error(self):
        responses.add(
            responses.GET,
            f"{PIRATE_BAY_BASE_URL}/q.php",
            body=Exception("Network error"),
        )
        assert search_pirate_bay("test") == []
