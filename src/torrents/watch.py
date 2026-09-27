"""Helpers for the watch folder, where dropped .torrent files are added automatically.

The polling loop is `WatchFolderWorker` in `workers`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from utils.logger import setup_logger

logger = setup_logger("torrents.watch")

PROCESSED_SUFFIX = ".processed"


def discover(folder: str) -> Iterable[str]:
    """Paths of the .torrent files in `folder` that have not been processed yet."""
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
    """Rename the file so the next poll does not add it again."""
    try:
        target = path + PROCESSED_SUFFIX
        if os.path.exists(target):
            os.remove(target)
        os.rename(path, target)
    except OSError as exc:
        logger.warning(f"Could not mark {path} as processed: {exc}")
