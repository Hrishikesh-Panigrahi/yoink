"""Reload torrents persisted across runs."""

from __future__ import annotations

import os

import libtorrent as lt

import db
from torrents.resume import load_resume_data
from torrents.session import Session
from utils.logger import setup_logger

logger = setup_logger("torrents.persistence")


def load_saved(session: Session) -> int:
    """Re-add every previously saved torrent to the session.

    Returns the number of torrents restored.
    """
    saved = db.list_torrents()
    restored = 0
    for row in saved:
        try:
            if not os.path.exists(row.save_path):
                os.makedirs(row.save_path, exist_ok=True)

            if row.magnet_link.startswith("magnet:"):
                params = lt.parse_magnet_uri(row.magnet_link)
                params.save_path = row.save_path
                resume_data = load_resume_data(row.info_hash)
                if resume_data:
                    params.resume_data = resume_data
                handle = session.lt_session.add_torrent(params)
            elif os.path.exists(row.magnet_link):
                info = lt.torrent_info(row.magnet_link)
                params = lt.add_torrent_params()
                params.ti = info
                params.save_path = row.save_path
                resume_data = load_resume_data(row.info_hash)
                if resume_data:
                    params.resume_data = resume_data
                handle = session.lt_session.add_torrent(params)
            else:
                logger.warning(f"Skipping saved torrent {row.name}: source missing")
                continue

            session.handles[row.info_hash.lower()] = handle
            if (row.status or "").lower() == "paused":
                try:
                    handle.unset_flags(lt.torrent_flags.auto_managed)
                except Exception:
                    pass
                handle.pause()
            else:
                try:
                    handle.set_flags(lt.torrent_flags.auto_managed)
                except Exception:
                    pass
                handle.resume()
            restored += 1
        except Exception as exc:
            logger.error(f"Failed to restore torrent {row.name}: {exc}")
    logger.info(f"Restored {restored} torrent(s) from database")
    return restored
