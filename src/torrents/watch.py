"""Watch-folder support: auto-add .torrent files dropped in a directory.

The actual polling worker lives in :mod:`workers`. This module exposes the
helpers it calls — listing candidate files and moving processed ones aside.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from utils.logger import setup_logger

logger = setup_logger("torrents.watch")

PROCESSED_SUFFIX = ".processed"


def discover(folder: str) -> Iterable[str]:
    """Yield absolute paths of unprocessed .torrent files in ``folder``."""
    if not folder:
        return []
    root = Path(folder)
    if not root.is_dir():
        return []
    return [
        str(p)
        for p in root.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".torrent"
        and not p.name.endswith(PROCESSED_SUFFIX)
    ]


def mark_processed(path: str) -> None:
    """Rename a .torrent file once we've fed it to libtorrent so we don't re-add it."""
    try:
        target = path + PROCESSED_SUFFIX
        if os.path.exists(target):
            os.remove(target)
        os.rename(path, target)
    except OSError as exc:
        logger.warning(f"Could not mark {path} as processed: {exc}")
