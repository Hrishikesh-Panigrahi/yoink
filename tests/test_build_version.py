"""Tests for the version parsing the release pipeline depends on.

This exists because it broke in a way nobody would notice until a release was
already published. `src/version.py`'s docstring mentions ``__version__`` as well
as assigning it, and the release workflow's `Select-String "__version__"` matched
both lines - so v2.1.0 shipped as `Yoink-Setup-__version__.exe`, with
`__version__` registered as the installer's version in Add/Remove Programs.

`build.py` is now the only parser, and CI calls it via `--print-version`.
"""

from __future__ import annotations

import re
import subprocess
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
    """The exact shape that broke the release."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "version.py").write_text(
        '"""Single source of truth for the application version.\n'
        "\n"
        "`build.py`, `setup.py`, the About panel, and the auto-updater all read\n"
        "``__version__`` from here. Bumping the release is a one-line change.\n"
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


def test_print_version_is_a_bare_version_on_stdout():
    """This is what the release workflow consumes; stray output would break it."""
    result = subprocess.run(
        [sys.executable, "build.py", "--print-version"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    printed = result.stdout.strip()

    from version import __version__

    assert printed == __version__
    assert SEMVER.match(printed)
    assert "\n" not in printed
