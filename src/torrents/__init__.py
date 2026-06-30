"""Torrent layer: function-based wrappers over a small `Session` object."""

from torrents.actions import add_magnet, add_torrent_file, pause, remove, resume
from torrents.dto import NetworkStats, TorrentSnapshot
from torrents.persistence import load_saved
from torrents.session import Session, create_session, network_stats, set_save_path, stop_session
from torrents.state import list_torrents

__all__ = [
    "Session",
    "create_session",
    "stop_session",
    "set_save_path",
    "network_stats",
    "add_magnet",
    "add_torrent_file",
    "pause",
    "resume",
    "remove",
    "list_torrents",
    "load_saved",
    "TorrentSnapshot",
    "NetworkStats",
]
