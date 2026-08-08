"""Torrent layer: function-based wrappers over a small `Session` object."""

from torrents.actions import (
    add_magnet,
    add_magnet_verbose,
    add_torrent_file,
    pause,
    pause_all,
    remove,
    resume,
    resume_all,
    set_file_priorities,
)
from torrents.dto import (
    NetworkStats,
    StreamPlan,
    StreamStatus,
    TorrentFile,
    TorrentSnapshot,
)
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
from torrents.streaming import (
    pick_video_file,
    plan_stream,
    start_stream,
    stop_stream,
    stream_status,
)

__all__ = [
    "Session",
    "create_session",
    "stop_session",
    "set_save_path",
    "network_stats",
    "apply_limits",
    "enforce_seed_ratio",
    "add_magnet",
    "add_magnet_verbose",
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
    "start_stream",
    "stop_stream",
    "stream_status",
    "plan_stream",
    "pick_video_file",
    "TorrentSnapshot",
    "TorrentFile",
    "NetworkStats",
    "StreamPlan",
    "StreamStatus",
]
