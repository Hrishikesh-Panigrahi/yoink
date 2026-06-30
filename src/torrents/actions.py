"""Add, pause, resume, and remove torrents."""

from __future__ import annotations

import os
from typing import Optional

import libtorrent as lt

import db
from torrents.session import Session
from utils.logger import setup_logger
from utils.paths import normalize_path

logger = setup_logger("torrents.actions")


def add_magnet(session: Session, magnet: str, save_path: Optional[str] = None) -> str:
    """Add a torrent from a magnet URI. Returns its info hash (lowercase)."""
    if not magnet or not magnet.startswith("magnet:"):
        raise ValueError("Invalid magnet link")

    destination = normalize_path(save_path or session.save_path)
    os.makedirs(destination, exist_ok=True)

    params = lt.parse_magnet_uri(magnet)
    info_hash = str(params.info_hash).lower()
    if info_hash in session.handles:
        logger.info(f"Torrent already added: {info_hash}")
        return info_hash

    params.save_path = destination
    handle = session.lt_session.add_torrent(params)
    session.handles[info_hash] = handle

    name = params.name or info_hash
    db.save_torrent(info_hash=info_hash, name=name, magnet_link=magnet, save_path=destination)

    logger.info(f"Added magnet torrent {info_hash} ({name})")
    return info_hash


def add_torrent_file(session: Session, file_path: str, save_path: Optional[str] = None) -> str:
    """Add a torrent from a `.torrent` file. Returns its info hash (lowercase)."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Torrent file not found: {file_path}")

    destination = normalize_path(save_path or session.save_path)
    os.makedirs(destination, exist_ok=True)

    info = lt.torrent_info(file_path)
    params = lt.add_torrent_params()
    params.ti = info
    params.save_path = destination
    handle = session.lt_session.add_torrent(params)
    info_hash = str(handle.info_hash()).lower()
    session.handles[info_hash] = handle

    db.save_torrent(
        info_hash=info_hash,
        name=info.name(),
        magnet_link=file_path,
        save_path=destination,
        size=info.total_size(),
    )

    logger.info(f"Added .torrent file {info_hash} ({info.name()})")
    return info_hash


def pause(session: Session, info_hash: str) -> bool:
    """Pause a torrent by info hash."""
    handle = session.handles.get(info_hash.lower())
    if handle is None:
        return False
    handle.pause()
    db.update_torrent_status(info_hash, "paused")
    return True


def resume(session: Session, info_hash: str) -> bool:
    """Resume a paused torrent by info hash."""
    handle = session.handles.get(info_hash.lower())
    if handle is None:
        return False
    handle.resume()
    db.update_torrent_status(info_hash, "downloading")
    return True


def remove(session: Session, info_hash: str, delete_files: bool = False) -> bool:
    """Remove a torrent from the session and persistence, optionally deleting data."""
    key = info_hash.lower()
    handle = session.handles.get(key)
    if handle is None:
        return False

    save_path = handle.status().save_path
    files_to_delete: list[str] = []
    if delete_files and handle.has_metadata():
        info = handle.get_torrent_info()
        for idx in range(len(info.files())):
            candidate = os.path.join(save_path, info.files().file_path(idx))
            if os.path.exists(candidate):
                files_to_delete.append(candidate)

    try:
        session.lt_session.remove_torrent(handle)
    except Exception as exc:
        logger.error(f"libtorrent remove failed for {info_hash}: {exc}")

    db.remove_torrent(info_hash)
    session.handles.pop(key, None)

    if delete_files:
        for path in files_to_delete:
            try:
                os.remove(path)
            except OSError as exc:
                logger.warning(f"Could not delete {path}: {exc}")
        try:
            os.rmdir(save_path)
        except OSError:
            pass

    logger.info(f"Removed torrent {info_hash}")
    return True
