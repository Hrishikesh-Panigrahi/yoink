"""Add, pause, resume, and remove torrents."""

from __future__ import annotations

import os
from typing import Optional

import libtorrent as lt

import db
from torrents.resume import remove_resume_data
from torrents.session import Session
from utils.logger import setup_logger
from utils.paths import normalize_path

logger = setup_logger("torrents.actions")


def add_magnet(session: Session, magnet: str, save_path: Optional[str] = None) -> str:
    """Add a torrent from a magnet URI. Returns its info hash (lowercase)."""
    info_hash, _ = add_magnet_verbose(session, magnet, save_path)
    return info_hash


def add_magnet_verbose(
    session: Session, magnet: str, save_path: Optional[str] = None
) -> tuple[str, bool]:
    """Add a torrent and report whether it was already known.

    Returns ``(info_hash, was_existing)``.
    """
    if not magnet or not magnet.startswith("magnet:"):
        raise ValueError("Invalid magnet link")

    destination = normalize_path(save_path or session.save_path)
    os.makedirs(destination, exist_ok=True)

    params = lt.parse_magnet_uri(magnet)
    info_hash = str(params.info_hash).lower()
    if info_hash in session.handles:
        logger.info(f"Torrent already added: {info_hash}")
        return info_hash, True

    params.save_path = destination
    handle = session.lt_session.add_torrent(params)
    session.handles[info_hash] = handle

    name = params.name or info_hash
    db.save_torrent(info_hash=info_hash, name=name, magnet_link=magnet, save_path=destination)

    logger.info(f"Added magnet torrent {info_hash} ({name})")
    return info_hash, False


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


def set_file_priorities(session: Session, info_hash: str, priorities: dict[int, int]) -> bool:
    """Set per-file libtorrent priorities (0=skip, 1=low, 4=normal, 7=high)."""
    handle = session.handles.get(info_hash.lower())
    if handle is None or not handle.is_valid() or not handle.has_metadata():
        return False
    try:
        current = list(handle.file_priorities())
    except Exception as exc:
        logger.warning(f"file_priorities() read failed: {exc}")
        info = handle.get_torrent_info()
        current = [4] * info.files().num_files()

    changed = False
    for raw_idx, raw_prio in priorities.items():
        try:
            idx = int(raw_idx)
            prio = max(0, min(7, int(raw_prio)))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(current):
            current[idx] = prio
            changed = True

    if not changed:
        return False

    try:
        handle.prioritize_files(current)
    except Exception as exc:
        logger.error(f"prioritize_files failed for {info_hash}: {exc}")
        return False
    return True


def _clear_auto_managed(handle) -> None:
    """Drop the auto_managed flag so libtorrent's queue manager won't auto-resume."""
    try:
        handle.unset_flags(lt.torrent_flags.auto_managed)
    except Exception:
        pass


def _set_auto_managed(handle) -> None:
    """Restore the auto_managed flag so libtorrent can schedule the torrent again."""
    try:
        handle.set_flags(lt.torrent_flags.auto_managed)
    except Exception:
        pass


def pause_all(session: Session) -> int:
    """Pause every torrent in the session. Returns how many were paused."""
    count = 0
    for info_hash, handle in list(session.handles.items()):
        if handle is None or not handle.is_valid():
            continue
        _clear_auto_managed(handle)
        handle.pause()
        db.update_torrent_status(info_hash, "paused")
        count += 1
    return count


def resume_all(session: Session) -> int:
    """Resume every torrent in the session. Returns how many were resumed."""
    count = 0
    for info_hash, handle in list(session.handles.items()):
        if handle is None or not handle.is_valid():
            continue
        _set_auto_managed(handle)
        handle.resume()
        db.update_torrent_status(info_hash, "downloading")
        count += 1
    return count


def pause(session: Session, info_hash: str) -> bool:
    """Pause a torrent by info hash."""
    handle = session.handles.get(info_hash.lower())
    if handle is None:
        return False
    _clear_auto_managed(handle)
    handle.pause()
    db.update_torrent_status(info_hash, "paused")
    return True


def resume(session: Session, info_hash: str) -> bool:
    """Resume a paused torrent by info hash."""
    handle = session.handles.get(info_hash.lower())
    if handle is None:
        return False
    _set_auto_managed(handle)
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
    remove_resume_data(info_hash)
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
