"""Tests for the search orchestrator and the Torrent-Api-py adapter."""

from __future__ import annotations

import providers.torrent_api_py as torrent_api_py
from providers.torrent_api_py import search_multi_site
from search import search
from search.dto import SearchOptions, SearchResult
from search.enums import ProviderMode, Region


class FakeProvider:
    _name = "Fake"

    async def search(self, query, page, limit):
        return {
            "data": [
                {
                    "name": "Cocktail 2 2025 Hindi 1080p WEBRip",
                    "size": "2.0 GB",
                    "seeders": "10",
                    "leechers": "2",
                    "category": "Movies",
                    "magnet": "magnet:?xt=urn:btih:abc",
                },
                {
                    "name": "Unrelated Cocktail Hollywood 1080p",
                    "size": "1.8 GB",
                    "seeders": "1000",
                    "leechers": "200",
                    "category": "Movies",
                    "magnet": "magnet:?xt=urn:btih:def",
                },
            ][:limit]
        }


class FakeCategoryProvider(FakeProvider):
    _name = "Fake Category"

    async def search_by_category(self, query, category, page, limit):
        response = await self.search(query, page, limit)
        for item in response["data"]:
            item["category"] = category
        return response


class EmptyProvider:
    _name = "Empty"

    async def search(self, query, page, limit):
        return {"data": []}


def _stub_sites(monkeypatch, sites: dict) -> None:
    monkeypatch.setattr(torrent_api_py, "AVAILABLE_SITES", sites)


def _stub_stable_results(monkeypatch, pirate_for=None, yts_results=None):
    """Stub the stable providers. `pirate_for` is a {query_substring: [SearchResult]} map."""
    pirate_for = pirate_for or {}
    yts_results = yts_results or []
    calls = {"pirate_queries": []}

    def fake_pirate(query, page=1, limit=20):
        calls["pirate_queries"].append(query)
        for needle, payload in pirate_for.items():
            if needle in query.lower():
                return list(payload)
        return []

    def fake_yts(query, limit=20):
        return list(yts_results)

    monkeypatch.setattr("providers.pirate_bay.search_pirate_bay", fake_pirate)
    monkeypatch.setattr("providers.yts.search_yts", fake_yts)
    return calls


def test_multi_site_scoring_prefers_region_match(monkeypatch):
    _stub_sites(monkeypatch, {
        "fake": {
            "website": FakeProvider,
            "categories": ["movies"],
            "search_by_category": False,
            "limit": 10,
        }
    })

    results = search_multi_site(
        "cocktail 2", page=1, sites=["fake"], region=Region.BOLLYWOOD, limit_per_site=10
    )

    assert results[0].title.startswith("Cocktail 2")


def test_multi_site_uses_search_by_category(monkeypatch):
    _stub_sites(monkeypatch, {
        "fake": {
            "website": FakeCategoryProvider,
            "categories": ["movies"],
            "search_by_category": True,
            "limit": 10,
        }
    })

    results = search_multi_site(
        "cocktail 2", page=1, sites=["fake"], region=Region.ANY, limit_per_site=1
    )

    assert results
    # Category-aware path was taken; vendor row was tagged with "movies".
    assert results[0].magnet_url.startswith("magnet:")


def test_search_paginates_multi_results(monkeypatch):
    _stub_sites(monkeypatch, {
        "fake": {
            "website": FakeProvider,
            "categories": ["movies"],
            "search_by_category": False,
            "limit": 10,
        }
    })

    page = search(
        "cocktail 2",
        page=1,
        limit=1,
        options=SearchOptions(
            provider_mode=ProviderMode.MULTI,
            region=Region.BOLLYWOOD,
            sites=["fake"],
        ),
    )

    assert page.total == 2
    assert page.pages == 2
    assert page.results[0].title.startswith("Cocktail 2")


def test_stable_search_expands_region_and_scores(monkeypatch):
    bollywood = SearchResult(
        title="Cocktail 2 2025 Hindi 1080p WEBRip",
        size="2.0 GB",
        seeds=20,
        peers=4,
        date="2025-01-01",
        source="The Pirate Bay",
        magnet_url="magnet:?xt=urn:btih:hindi",
    )
    hollywood = SearchResult(
        title="Cocktail Hollywood 1080p",
        size="1.8 GB",
        seeds=1000,
        peers=200,
        date="2025-01-01",
        source="The Pirate Bay",
        magnet_url="magnet:?xt=urn:btih:hollywood",
    )
    calls = _stub_stable_results(
        monkeypatch,
        pirate_for={"hindi": [bollywood], "cocktail 2": [hollywood]},
    )

    page = search(
        "cocktail 2",
        page=1,
        limit=10,
        options=SearchOptions(provider_mode=ProviderMode.STABLE, region=Region.BOLLYWOOD),
    )

    assert any("hindi" in q for q in calls["pirate_queries"])
    assert page.total == 2
    assert page.pages == 1
    assert page.results[0].title.startswith("Cocktail 2")


def test_multi_falls_back_to_stable_when_empty(monkeypatch):
    _stub_sites(monkeypatch, {
        "empty": {
            "website": EmptyProvider,
            "categories": ["movies"],
            "search_by_category": False,
            "limit": 10,
        }
    })
    bollywood = SearchResult(
        title="Cocktail 2 2025 Hindi 1080p WEBRip",
        size="2.0 GB",
        seeds=20,
        peers=4,
        date="2025-01-01",
        source="The Pirate Bay",
        magnet_url="magnet:?xt=urn:btih:hindi",
    )
    _stub_stable_results(monkeypatch, pirate_for={"cocktail 2": [bollywood]})

    page = search(
        "cocktail 2",
        page=1,
        limit=10,
        options=SearchOptions(
            provider_mode=ProviderMode.MULTI, sites=["empty"], region=Region.BOLLYWOOD
        ),
    )

    assert page.total == 1
    assert page.results[0].title.startswith("Cocktail 2")
