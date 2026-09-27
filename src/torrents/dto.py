from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TorrentSnapshot:
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
    index: int
    path: str
    size: int  # bytes
    size_str: str
    progress: float  # 0-100
    priority: int  # libtorrent scale: 0 skip, 1 low, 4 normal, 7 high

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
    download_kb_s: float
    upload_kb_s: float


@dataclass(frozen=True)
class StreamPlan:
    """Pieces of one file that must arrive first for playback to start.

    `head_pieces` and `tail_pieces` never overlap. On a file small enough for
    them to meet, the shared pieces stay in the head.
    """

    first_piece: int
    last_piece: int
    head_pieces: tuple[int, ...]
    tail_pieces: tuple[int, ...]


@dataclass(frozen=True)
class StreamStatus:
    """How close a file is to being playable while it downloads."""

    info_hash: str
    file_index: int
    path: str  # relative to the save path
    absolute_path: str
    size: int
    first_piece: int
    last_piece: int
    head_have: int  # head pieces downloaded so far
    head_total: int
    tail_have: int
    tail_total: int
    sequential: bool  # torrent is in sequential download mode

    @property
    def ready(self) -> bool:
        """True once a player can open the file without stalling immediately."""
        return self.head_have >= self.head_total and self.tail_have >= self.tail_total

    def to_dict(self) -> dict:
        required = self.head_total + self.tail_total
        have = self.head_have + self.tail_have
        return {
            "hash": self.info_hash,
            "fileIndex": self.file_index,
            "path": self.path,
            "absolutePath": self.absolute_path,
            "size": self.size,
            "firstPiece": self.first_piece,
            "lastPiece": self.last_piece,
            "headHave": self.head_have,
            "headTotal": self.head_total,
            "tailHave": self.tail_have,
            "tailTotal": self.tail_total,
            "bufferProgress": (have / required * 100.0) if required else 0.0,
            "sequential": self.sequential,
            "ready": self.ready,
        }
