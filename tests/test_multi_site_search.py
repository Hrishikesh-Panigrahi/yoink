"""Tests for the search orchestrator and the Torrent-Api-py adapter."""

from __future__ import annotations

import providers.torrent_api_py as torrent_api_py
from providers.torrent_api_py import search_multi_site
from search import search
from search.dto import SearchOptions, SearchResult
from search.enums import Category, ProviderMode, Region


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


def _stub_stable_results(monkeypatch, pirate_for=None):
    """Stub The Pirate Bay. `pirate_for` maps a query substring to its results."""
    pirate_for = pirate_for or {}
    calls = {"pirate_queries": [], "categories": []}

    def fake_pirate(query, page=1, limit=20, category=Category.ANY):
        calls["pirate_queries"].append(query)
        calls["categories"].append(category)
        for needle, payload in pirate_for.items():
            if needle in query.lower():
                return list(payload)
        return []

    monkeypatch.setattr("providers.pirate_bay.search_pirate_bay", fake_pirate)
    return calls


class MixedProvider:
    _name = "Mixed"

    async def search(self, query, page, limit):
        rows = [
            ("Grounded PC Game Repack", "Games"),
            ("Grounded 2024 1080p WEB-DL", "Movies"),
            ("Grounded S01E01 720p", ""),
            ("Grounded", ""),
        ]
        return {"data": [
            {"name": name, "category": label, "seeders": "5", "magnet": f"magnet:?xt=urn:btih:{i}"}
            for i, (name, label) in enumerate(rows)
        ]}


def _mixed_site(monkeypatch, key="mixed"):
    _stub_sites(monkeypatch, {
        key: {"website": MixedProvider, "categories": [], "search_by_category": False, "limit": 10}
    })


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


def test_multi_site_filters_rows_by_category(monkeypatch):
    _mixed_site(monkeypatch)

    titles = [r.title for r in search_multi_site(
        "grounded", sites=["mixed"], category=Category.GAMES, limit_per_site=10
    )]

    # The unlabelled, unrecognisable "Grounded" row is kept rather than guessed at.
    assert sorted(titles) == ["Grounded", "Grounded PC Game Repack"]


def test_multi_site_uses_titles_when_rows_have_no_label(monkeypatch):
    _mixed_site(monkeypatch)

    titles = [r.title for r in search_multi_site(
        "grounded", sites=["mixed"], category=Category.TV, limit_per_site=10
    )]

    assert sorted(titles) == ["Grounded", "Grounded S01E01 720p"]


def test_libgen_rows_count_as_books(monkeypatch):
    _mixed_site(monkeypatch, key="libgen")

    movies = search_multi_site("grounded", sites=["libgen"], category=Category.MOVIES, limit_per_site=10)
    books = search_multi_site("grounded", sites=["libgen"], category=Category.BOOKS, limit_per_site=10)

    # Rows with their own label keep it; unlabelled libgen rows are books.
    assert [r.title for r in movies] == ["Grounded 2024 1080p WEB-DL"]
    assert sorted(r.title for r in books) == ["Grounded", "Grounded S01E01 720p"]


def test_falls_back_to_stable_when_the_category_filters_everything(monkeypatch):
    _stub_sites(monkeypatch, {
        "fake": {"website": FakeProvider, "categories": ["movies"], "search_by_category": False, "limit": 10}
    })
    game = SearchResult(
        title="Grounded PC Game", size="5 GB", seeds=50, peers=5, date="2025-01-01",
        source="The Pirate Bay", magnet_url="magnet:?xt=urn:btih:game",
    )
    calls = _stub_stable_results(monkeypatch, pirate_for={"cocktail": [game]})

    page = search(
        "cocktail",
        options=SearchOptions(provider_mode=ProviderMode.MULTI, sites=["fake"], category=Category.GAMES),
    )

    assert [r.title for r in page.results] == ["Grounded PC Game"]
    assert calls["categories"] == [Category.GAMES]


def test_all_enabled_sites_also_searches_the_pirate_bay(monkeypatch):
    _stub_sites(monkeypatch, {
        "fake": {"website": FakeProvider, "categories": ["movies"], "search_by_category": False, "limit": 10}
    })
    tpb = SearchResult(
        title="Cocktail 2 from the Pirate Bay API", size="2 GB", seeds=30, peers=3, date="2025-01-01",
        source="The Pirate Bay", magnet_url="magnet:?xt=urn:btih:tpb",
    )
    _stub_stable_results(monkeypatch, pirate_for={"cocktail": [tpb]})

    page = search("cocktail 2", options=SearchOptions.from_dict({
        "providerMode": "multi", "sites": ["fake"], "includeStable": True,
    }))

    titles = {r.title for r in page.results}
    assert "Cocktail 2 from the Pirate Bay API" in titles
    assert len(titles) == 3

