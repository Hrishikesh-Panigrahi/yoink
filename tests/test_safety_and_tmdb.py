"""Tests for safety scoring and TMDB cache / key resolution."""

from __future__ import annotations

import os
import tempfile

import pytest
import responses

import db
from providers import tmdb
from search.safety import evaluate


@pytest.fixture
def tmp_db(monkeypatch):
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    handle.close()
    monkeypatch.setenv("TORRENT_DB_PATH", handle.name)
    db.dispose_engine()
    db.init_db()
    yield handle.name
    db.dispose_engine()
    if os.path.exists(handle.name):
        os.remove(handle.name)


# --------- Safety ---------

class TestSafety:
    def test_safe_when_trusted_group(self):
        result = evaluate({
            "title": "The Matrix 1999 1080p BluRay x264-YTS",
            "source": "yts",
            "seeds": 200,
            "size": "1.5 GB",
            "magnet": "magnet:?xt=urn:btih:abc",
        })
        assert result["level"] == "safe"

    def test_risky_when_exe_in_title(self):
        result = evaluate({
            "title": "movie.installer.exe",
            "source": "Unknown",
            "seeds": 5,
            "size": "10 MB",
            "magnet": "magnet:?xt=urn:btih:abc",
        })
        assert result["level"] == "risky"
        assert any(".exe" in r for r in result["reasons"])

    def test_caution_when_no_seeders(self):
        result = evaluate({
            "title": "Some Random Movie 2020 1080p WEBRip",
            "source": "1337x",
            "seeds": 0,
            "size": "1 GB",
            "magnet": "magnet:?xt=urn:btih:abc",
        })
        assert result["level"] in {"caution", "risky"}
        assert any("seeder" in r.lower() for r in result["reasons"])

    def test_risky_when_no_magnet(self):
        result = evaluate({
            "title": "Movie 2024",
            "source": "1337x",
            "seeds": 100,
            "size": "1 GB",
            "magnet": "",
        })
        assert result["level"] == "risky"


# --------- TMDB ---------

class TestTmdbConfig:
    def test_get_api_key_prefers_setting(self, tmp_db, monkeypatch):
        db.set_setting("tmdb_api_key", "from_setting")
        monkeypatch.setenv("TMDB_API_KEY", "from_env")
        assert tmdb.get_api_key() == "from_setting"

    def test_get_api_key_falls_back_to_env(self, tmp_db, monkeypatch):
        db.set_setting("tmdb_api_key", "")
        monkeypatch.setenv("TMDB_API_KEY", "from_env")
        assert tmdb.get_api_key() == "from_env"

    def test_get_api_key_none_when_unset(self, tmp_db, monkeypatch):
        db.set_setting("tmdb_api_key", "")
        monkeypatch.delenv("TMDB_API_KEY", raising=False)
        assert tmdb.get_api_key() is None

    def test_enrich_returns_none_without_key(self, tmp_db, monkeypatch):
        db.set_setting("tmdb_api_key", "")
        monkeypatch.delenv("TMDB_API_KEY", raising=False)
        assert tmdb.enrich("Matrix", 1999) is None


class TestTmdbEnrich:
    @responses.activate
    def test_enrich_happy_path_writes_cache(self, tmp_db, monkeypatch):
        db.set_setting("tmdb_api_key", "fake_key")
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/search/movie",
            json={
                "results": [{
                    "id": 603,
                    "title": "The Matrix",
                    "release_date": "1999-03-30",
                    "vote_average": 8.2,
                }]
            },
        )
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/movie/603",
            json={
                "id": 603,
                "title": "The Matrix",
                "release_date": "1999-03-30",
                "vote_average": 8.2,
                "runtime": 136,
                "genres": [{"id": 1, "name": "Action"}],
                "overview": "Neo learns the truth.",
                "poster_path": "/p.jpg",
                "backdrop_path": "/b.jpg",
                "videos": {"results": [{"site": "YouTube", "type": "Trailer", "key": "abc"}]},
                "external_ids": {"imdb_id": "tt0133093"},
            },
        )

        meta = tmdb.enrich("The Matrix", 1999)
        assert meta is not None
        assert meta["tmdbId"] == 603
        assert meta["rating"] == pytest.approx(8.2)
        assert meta["runtime"] == 136
        assert meta["poster"].endswith("/p.jpg")
        assert "Action" in meta["genres"]
        assert meta["trailerUrl"].endswith("?v=abc")
        assert meta["imdbUrl"].endswith("tt0133093/")

        # Cache should be hit on the second call -> no extra HTTP requests.
        responses.reset()
        meta_cached = tmdb.enrich("The Matrix", 1999)
        assert meta_cached is not None
        assert meta_cached["tmdbId"] == 603

    @responses.activate
    def test_enrich_empty_search_caches_negative(self, tmp_db):
        db.set_setting("tmdb_api_key", "fake_key")
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/search/movie",
            json={"results": []},
        )
        assert tmdb.enrich("totally fake film name xyz", 2099) is None
        # Subsequent call should hit cache and skip the HTTP layer.
        responses.reset()
        assert tmdb.enrich("totally fake film name xyz", 2099) is None


# --------- Grouping by tmdbId (search dedupe + enrichment combination) ---------

class TestGroupingHelper:
    def test_normalize_title_used_for_cache_key(self):
        key_a = tmdb._cache_key("The Matrix 1999 1080p BluRay x264", 1999)
        key_b = tmdb._cache_key("The.Matrix.1999.720p.WEB-DL.x265", 1999)
        assert key_a == key_b
