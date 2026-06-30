"""Torrent layer: function-based wrappers over a small `Session` object."""

from torrents.actions import (
    add_magnet,
    add_torrent_file,
    pause,
    pause_all,
    remove,
    resume,
    resume_all,
    set_file_priorities,
)
from torrents.dto import NetworkStats, TorrentFile, TorrentSnapshot
from torrents.persistence import load_saved
from torrents.session import (
    Session,
    apply_limits,
    create_session,
    enforce_seed_ratio,
    network_stats,
    set_save_path,
    stop_session,
)
from torrents.state import list_files, list_torrents

__all__ = [
    "Session",
    "create_session",
    "stop_session",
    "set_save_path",
    "network_stats",
    "apply_limits",
    "enforce_seed_ratio",
    "add_magnet",
    "add_torrent_file",
    "pause",
    "resume",
    "remove",
    "pause_all",
    "resume_all",
    "set_file_priorities",
    "list_torrents",
    "list_files",
    "load_saved",
    "TorrentSnapshot",
    "TorrentFile",
    "NetworkStats",
]
