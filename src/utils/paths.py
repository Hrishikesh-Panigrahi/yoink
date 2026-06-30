"""Filesystem path helpers shared by the torrents and bridge layers."""

from __future__ import annotations

import os


def normalize_path(path: str) -> str:
    """Return an absolute, native, expanded version of `path`.

    Always call this before persisting a save folder or handing it to libtorrent.
    """
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))
