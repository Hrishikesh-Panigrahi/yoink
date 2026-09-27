"""Tests for the Pirate Bay provider."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlparse

import responses

import providers.pirate_bay as pirate_bay
from providers.pirate_bay import PIRATE_BAY_BASE_URL, search_pirate_bay
from search.enums import Category

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


def _row(info_hash, name, category):
    row = {"id": info_hash, "info_hash": info_hash * 40, "name": name, "size": "1000",
           "seeders": "5", "leechers": "1", "added": "1700000000"}
    if category is not None:
        row["category"] = category
    return row


@responses.activate
def test_sends_the_category_to_apibay(monkeypatch):
    monkeypatch.setattr(pirate_bay, "_throttle", lambda: None)
    responses.add(responses.GET, f"{PIRATE_BAY_BASE_URL}/q.php", json=[], status=200)

    search_pirate_bay("grounded", category=Category.GAMES)
    search_pirate_bay("dune", category=Category.MOVIES)
    search_pirate_bay("dune", category=Category.ANY)

    sent = [parse_qs(urlparse(call.request.url).query)["cat"][0] for call in responses.calls]
    assert sent == ["400", "201,202,207,209,210,211", "0"]


@responses.activate
def test_drops_rows_from_other_categories(monkeypatch):
    monkeypatch.setattr(pirate_bay, "_throttle", lambda: None)
    rows = [
        _row("a", "Grounded PC Game", "401"),
        _row("b", "Grounded S02E01 720p", "208"),
        _row("c", "Grounded Adult Parody", "505"),
        _row("d", "Grounded with no category field", None),
    ]
    responses.add(responses.GET, f"{PIRATE_BAY_BASE_URL}/q.php", json=rows, status=200)

    titles = [r.title for r in search_pirate_bay("grounded", category=Category.GAMES)]

    assert titles == ["Grounded PC Game", "Grounded with no category field"]


@responses.activate
def test_any_category_keeps_everything(monkeypatch):
    monkeypatch.setattr(pirate_bay, "_throttle", lambda: None)
    rows = [_row("a", "One", "401"), _row("b", "Two", "208"), _row("c", "Three", "505")]
    responses.add(responses.GET, f"{PIRATE_BAY_BASE_URL}/q.php", json=rows, status=200)

    assert len(search_pirate_bay("anything", category=Category.ANY)) == 3

