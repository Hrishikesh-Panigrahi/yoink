"""Unit tests for the search ranking + normalization helpers."""

from __future__ import annotations

from search.dto import SearchResult
from search.enums import Quality, Region, SortBy
from search.ranking import (
    SOURCE_WEIGHTS,
    dedupe_results,
    filter_by_min_seeds,
    filter_by_quality,
    health_score,
    normalize_title,
    sort_results,
)


def make_result(
    title: str,
    *,
    seeds: int = 0,
    source: str = "yts",
    magnet: str | None = None,
    quality: str = "1080p",
    size: str = "1.5 GB",
    date: str | None = None,
    summary: str = "",
    language: str = "",
) -> SearchResult:
    return SearchResult(
        title=title,
        size=size,
        seeds=seeds,
        peers=max(0, seeds // 2),
        date=date or "",
        source=source,
        magnet_url=magnet or f"magnet:?xt=urn:btih:{title.replace(' ', '')}",
        quality=quality,
        summary=summary,
        language=language,
    )


class TestNormalizeTitle:
    def test_strips_quality_and_group_and_year(self):
        assert (
            normalize_title("Cocktail.2.2024.1080p.WEBRip.x265-RARBG")
            == "cocktail 2"
        )

    def test_strips_brackets_and_codecs(self):
        assert (
            normalize_title("[YTS.MX] The Matrix (1999) [1080p] [BluRay] [5.1] [YTS]")
            == "the matrix"
        )

    def test_collapses_whitespace(self):
        assert normalize_title("  Foo   Bar  ") == "foo bar"

    def test_handles_empty(self):
        assert normalize_title("") == ""


class TestDedupe:
    def test_merges_by_magnet_keeps_higher_seeds(self):
        a = make_result("Movie 1080p", seeds=10, magnet="magnet:?xt=urn:btih:abc")
        b = make_result("Movie 1080p", seeds=50, magnet="magnet:?xt=urn:btih:abc")
        result = dedupe_results([a, b])
        assert len(result) == 1
        assert result[0].seeds == 50

    def test_collapses_same_release_across_providers(self):
        a = make_result("Cocktail.2.2024.1080p.x265-RARBG", seeds=100, source="1337x", magnet="magnet:?xt=urn:btih:a")
        b = make_result("Cocktail 2 (2024) 1080p WEB-DL [YTS]", seeds=200, source="yts", magnet="magnet:?xt=urn:btih:b")
        result = dedupe_results([a, b])
        assert len(result) == 1
        assert result[0].seeds == 200

    def test_keeps_distinct_titles(self):
        a = make_result("Foo 2024 1080p", seeds=5, magnet="magnet:?xt=urn:btih:x")
        b = make_result("Bar 2024 1080p", seeds=5, magnet="magnet:?xt=urn:btih:y")
        assert len(dedupe_results([a, b])) == 2


class TestFilters:
    def test_filter_by_quality_matches_token(self):
        a = make_result("Foo 1080p", quality="1080p")
        b = make_result("Foo 720p", quality="720p")
        assert filter_by_quality([a, b], Quality.HD_720P) == [b]

    def test_filter_by_quality_any_is_passthrough(self):
        items = [make_result("a"), make_result("b")]
        assert filter_by_quality(items, Quality.ANY) == items

    def test_filter_by_min_seeds(self):
        a = make_result("a", seeds=5)
        b = make_result("b", seeds=50)
        assert filter_by_min_seeds([a, b], 20) == [b]


class TestSort:
    def test_sort_by_seeds(self):
        a = make_result("a", seeds=10)
        b = make_result("b", seeds=100)
        assert sort_results([a, b], SortBy.SEEDS, "", Region.ANY)[0].seeds == 100

    def test_sort_by_size(self):
        a = make_result("a", size="500 MB")
        b = make_result("b", size="2.5 GB")
        result = sort_results([a, b], SortBy.SIZE, "", Region.ANY)
        assert result[0].size == "2.5 GB"

    def test_sort_by_newest_handles_missing(self):
        a = make_result("a", date="2010")
        b = make_result("b", date="2024")
        c = make_result("c", date="")
        result = sort_results([a, b, c], SortBy.NEWEST, "", Region.ANY)
        assert result[0].date == "2024"


class TestHealthScore:
    def test_token_match_beats_no_match(self):
        match = make_result("The Matrix 1080p", seeds=10, source="yts")
        miss = make_result("Random Thing 1080p", seeds=10, source="yts")
        assert health_score(match, "matrix", Region.ANY) > health_score(miss, "matrix", Region.ANY)

    def test_source_weight_breaks_ties(self):
        yts = make_result("Foo", seeds=10, source="yts")
        weak = make_result("Foo", seeds=10, source="torrentfunk")
        assert health_score(yts, "foo", Region.ANY) > health_score(weak, "foo", Region.ANY)

    def test_known_sources_have_weights(self):
        for key in ("yts", "the pirate bay", "1337x"):
            assert key in SOURCE_WEIGHTS
