"""Read-only view over the live libtorrent session."""

from __future__ import annotations

from typing import List

import libtorrent as lt

from torrents.dto import TorrentSnapshot
from torrents.session import Session
from utils.format import format_eta, format_size, format_speed
from utils.logger import setup_logger

logger = setup_logger("torrents.state")

_STATE_NAMES = {
    lt.torrent_status.queued_for_checking: "Queued",
    lt.torrent_status.checking_files: "Checking",
    lt.torrent_status.downloading_metadata: "Downloading Metadata",
    lt.torrent_status.downloading: "Downloading",
    lt.torrent_status.finished: "Finished",
    lt.torrent_status.seeding: "Seeding",
    lt.torrent_status.allocating: "Allocating",
    lt.torrent_status.checking_resume_data: "Checking Resume Data",
}


def list_torrents(session: Session) -> List[TorrentSnapshot]:
    """Return a snapshot for every active torrent in the session."""
    snapshots: List[TorrentSnapshot] = []
    for handle in session.lt_session.get_torrents():
        if not handle.is_valid():
            continue
        info_hash = str(handle.info_hash()).lower()
        session.handles.setdefault(info_hash, handle)
        snapshots.append(_snapshot(handle, info_hash))
    return snapshots


def _snapshot(handle: lt.torrent_handle, info_hash: str) -> TorrentSnapshot:
    status = handle.status()
    name = "Unknown"
    total_size = 0
    if handle.has_metadata():
        try:
            info = handle.get_torrent_info()
            name = info.name()
            total_size = info.total_size()
        except Exception as exc:
            logger.error(f"get_torrent_info failed: {exc}")

    if not handle.has_metadata():
        status_label = "Downloading Metadata"
    elif status.paused:
        status_label = "Paused"
    else:
        status_label = _STATE_NAMES.get(status.state, "Unknown")

    if status_label == "Downloading" and status.download_rate > 0 and total_size:
        remaining = total_size * (1 - status.progress)
        eta = format_eta(remaining / status.download_rate)
    elif status_label == "Seeding":
        eta = "Seeding"
    elif status_label == "Paused":
        eta = "Paused"
    else:
        eta = "Unknown"

    return TorrentSnapshot(
        info_hash=info_hash,
        name=name,
        size=format_size(total_size) if total_size else "Unknown",
        status=status_label,
        progress=float(status.progress) * 100.0,
        download_speed=format_speed(status.download_rate),
        upload_speed=format_speed(status.upload_rate),
        seeds=int(status.num_seeds or 0),
        peers=int(status.num_peers or 0),
        error=str(status.error) if status.error else "",
        save_path=status.save_path,
        eta=eta,
    )
