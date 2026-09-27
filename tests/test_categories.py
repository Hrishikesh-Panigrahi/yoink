"""Tests for search.categories, which guesses a result's category when a site can't filter."""

from __future__ import annotations

import pytest

from search.categories import ADULT, VIDEO, classify, from_label, from_title, matches
from search.enums import Category


@pytest.mark.parametrize("label, expected", [
    ("Movies", Category.MOVIES),
    ("TV", Category.TV),
    ("Games", Category.GAMES),
    ("Apps", Category.APPS),
    ("Anime", Category.ANIME),
    ("Audio", Category.MUSIC),
    ("Audio books", Category.BOOKS),
    ("Literature", Category.BOOKS),
    ("Software", Category.APPS),
    ("Documentaries", Category.MOVIES),
    ("Video", VIDEO),
    ("XXX", ADULT),
    ("Other", None),
    ("", None),
])
def test_site_labels(label, expected):
    assert from_label(label) == expected


@pytest.mark.parametrize("title, expected", [
    ("The Office S03E04 720p HDTV", Category.TV),
    ("[SubsPlease] One Piece - 1179 (1080p)", Category.ANIME),
    ("Grounded-FitGirl Repack", Category.GAMES),
    ("Dune Part Two 2024 1080p WEB-DL", Category.MOVIES),
    ("Pink Floyd Discography FLAC", Category.MUSIC),
    ("Adobe Photoshop 2024 x64 Pre-Activated", Category.APPS),
    ("Python Crash Course 3rd Edition EPUB", Category.BOOKS),
    ("Some Random Name", None),
])
def test_titles(title, expected):
    assert from_title(title) == expected


def test_the_label_wins_over_the_title():
    assert classify("Games", "Grounded S01E01") == Category.GAMES


def test_a_video_label_is_narrowed_by_the_title():
    assert classify("Video", "Grounded S01E01 720p") == Category.TV
    assert classify("Video", "Grounded") == VIDEO


def test_matches():
    assert matches(Category.GAMES, "Games", "Grounded")
    assert not matches(Category.GAMES, "TV", "Grounded")
    assert matches(Category.MOVIES, "Video", "Grounded")
    assert matches(Category.TV, "Video", "Grounded")
    assert matches(Category.ANIME, "TV", "Grounded")
    assert not matches(Category.MOVIES, "XXX", "Grounded")
    assert matches(Category.ANY, "XXX", "Grounded")
    # Nothing to go on, so the result is kept.
    assert matches(Category.BOOKS, "", "Grounded")
