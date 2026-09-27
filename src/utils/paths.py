from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Yoink"


def normalize_path(path: str) -> str:
    """Use this on a save folder before storing it or passing it to libtorrent."""
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def app_data_dir(*parts: str, create: bool = True) -> str:
    """Return Yoink's data folder under the user's profile.

    Packaged installs can live in Program Files, which isn't writable.
    """
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    path = base / APP_DIR_NAME
    for part in parts:
        path = path / part
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return str(path)


def logs_dir() -> str:
    return app_data_dir("logs")


def default_db_path() -> str:
    return app_data_dir("yoink.db", create=False)


def default_log_path() -> str:
    return str(Path(logs_dir()) / "yoink.log")
