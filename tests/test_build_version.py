"""Tests for how `build.py` reads the app version from `src/version.py`."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

SEMVER = re.compile(r"^\d+\.\d+\.\d+")


def test_read_version_matches_the_module():
    from version import __version__

    assert build._read_version() == __version__


def test_read_version_looks_like_a_version():
    assert SEMVER.match(build._read_version()), build._read_version()


def test_read_version_ignores_a_docstring_mention(tmp_path, monkeypatch):
    """Mirrors `src/version.py`, whose docstring also mentions `__version__`."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "version.py").write_text(
        '"""Single source of truth for the application version.\n'
        "\n"
        "`build.py` and the About panel both read ``__version__`` from here.\n"
        '"""\n'
        "\n"
        '__version__ = "9.8.7"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "SRC", src)

    assert build._read_version() == "9.8.7"


def test_read_version_keeps_a_value_containing_an_equals_sign(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "version.py").write_text('__version__ = "1.2.3+build=7"\n', encoding="utf-8")
    monkeypatch.setattr(build, "SRC", src)

    assert build._read_version() == "1.2.3+build=7"


@pytest.mark.parametrize("quote", ['"', "'"])
def test_read_version_handles_either_quote(tmp_path, monkeypatch, quote):
    src = tmp_path / "src"
    src.mkdir()
    (src / "version.py").write_text(f"__version__ = {quote}4.5.6{quote}\n", encoding="utf-8")
    monkeypatch.setattr(build, "SRC", src)

    assert build._read_version() == "4.5.6"
