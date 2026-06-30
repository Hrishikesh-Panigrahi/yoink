"""Read-only view over the live libtorrent session."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List

import libtorrent as lt

from torrents.dto import TorrentFile, TorrentSnapshot
from torrents.session import Session
from utils.format import format_eta, format_size, format_speed
from utils.logger import setup_logger

logger = setup_logger("torrents.state")

# Smooths short-term spikes in libtorrent's download_rate when computing ETA.
# Each entry is a small ring buffer of recent (bytes/sec) samples per info hash.
_ETA_WINDOW: int = 8
_RATE_SAMPLES: Dict[str, Deque[float]] = {}

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

    if status_label == "Downloading" and total_size:
        smoothed_rate = _smooth_rate(info_hash, status.download_rate)
        if smoothed_rate > 0:
            remaining = total_size * (1 - status.progress)
            eta = format_eta(remaining / smoothed_rate)
        else:
            eta = "Stalled"
    elif status_label == "Seeding":
        eta = "Seeding"
    elif status_label == "Paused":
        eta = "Paused"
    else:
        eta = "Unknown"

    if status_label not in ("Downloading", "Downloading Metadata"):
        _RATE_SAMPLES.pop(info_hash, None)

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


def _smooth_rate(info_hash: str, current_rate: float) -> float:
    """Return a rolling average of recent download rates to stabilize ETA."""
    samples = _RATE_SAMPLES.setdefault(info_hash, deque(maxlen=_ETA_WINDOW))
    if current_rate and current_rate > 0:
        samples.append(float(current_rate))
    if not samples:
        return 0.0
    return sum(samples) / len(samples)


def list_files(session: Session, info_hash: str) -> List[TorrentFile]:
    """Return the file table for a torrent (empty list if metadata isn't ready)."""
    handle = session.handles.get(info_hash.lower())
    if handle is None or not handle.is_valid() or not handle.has_metadata():
        return []
    info = handle.get_torrent_info()
    files = info.files()

    try:
        priorities = list(handle.file_priorities())
    except Exception:
        priorities = [4] * files.num_files()

    try:
        progress_bytes = handle.file_progress()
    except Exception:
        progress_bytes = [0] * files.num_files()

    out: List[TorrentFile] = []
    for idx in range(files.num_files()):
        size = int(files.file_size(idx))
        downloaded = int(progress_bytes[idx]) if idx < len(progress_bytes) else 0
        progress = (downloaded / size * 100.0) if size else 0.0
        priority = int(priorities[idx]) if idx < len(priorities) else 4
        out.append(
            TorrentFile(
                index=idx,
                path=files.file_path(idx),
                size=size,
                size_str=format_size(size),
                progress=progress,
                priority=priority,
            )
        )
    return out
