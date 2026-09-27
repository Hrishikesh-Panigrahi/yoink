"""Save and load libtorrent fast-resume data."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import libtorrent as lt

from utils.logger import setup_logger
from utils.paths import app_data_dir

logger = setup_logger("torrents.resume")


def resume_path(info_hash: str) -> Path:
    safe_hash = "".join(ch for ch in info_hash.lower() if ch.isalnum())
    return Path(app_data_dir("resume")) / f"{safe_hash}.fastresume"


def load_resume_data(info_hash: str) -> Optional[bytes]:
    path = resume_path(info_hash)
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except OSError as exc:
        logger.warning(f"Could not read resume data for {info_hash}: {exc}")
        return None


def store_resume_data(info_hash: str, params) -> bool:
    """`params` comes from a `save_resume_data_alert`. Returns False if writing failed."""
    try:
        data = lt.write_resume_data_buf(params)
        resume_path(info_hash).write_bytes(bytes(data))
        return True
    except Exception as exc:
        logger.warning(f"Could not write resume data for {info_hash}: {exc}")
        return False


def remove_resume_data(info_hash: str) -> None:
    try:
        resume_path(info_hash).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning(f"Could not delete resume data for {info_hash}: {exc}")
