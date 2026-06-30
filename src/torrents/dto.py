"""DTOs describing live torrent state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class TorrentSnapshot:
    """A point-in-time snapshot of one torrent for the UI."""

    info_hash: str
    name: str
    size: str
    status: str
    progress: float  # 0-100
    download_speed: str
    upload_speed: str
    seeds: int
    peers: int
    error: str
    save_path: str
    eta: str

    def to_dict(self) -> dict:
        return {
            "hash": self.info_hash,
            "name": self.name,
            "size": self.size,
            "status": self.status,
            "progress": self.progress,
            "downloadSpeed": self.download_speed,
            "uploadSpeed": self.upload_speed,
            "seeds": self.seeds,
            "peers": self.peers,
            "error": self.error,
            "savePath": self.save_path,
            "eta": self.eta,
        }


@dataclass(frozen=True)
class TorrentFile:
    """One file inside a multi-file torrent."""

    index: int
    path: str
    size: int            # raw bytes for ordering
    size_str: str        # human-readable
    progress: float      # 0-100
    priority: int        # 0 skip, 1 low, 4 normal, 7 high (libtorrent scale)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "path": self.path,
            "size": self.size,
            "sizeStr": self.size_str,
            "progress": self.progress,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class NetworkStats:
    """Aggregate session-wide throughput in KB/s."""

    download_kb_s: float
    upload_kb_s: float
