"""DTOs describing live torrent state."""

from __future__ import annotations

from dataclasses import dataclass


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


@dataclass(frozen=True)
class StreamPlan:
    """Which pieces of one file have to arrive first for playback to start.

    `head_pieces` and `tail_pieces` never overlap: on a file small enough that
    the two windows would meet, everything lands in the head.
    """

    first_piece: int
    last_piece: int
    head_pieces: tuple[int, ...]
    tail_pieces: tuple[int, ...]

    @property
    def required_pieces(self) -> tuple[int, ...]:
        return self.head_pieces + self.tail_pieces


@dataclass(frozen=True)
class StreamStatus:
    """How close a file is to being playable while it downloads."""

    info_hash: str
    file_index: int
    path: str             # path inside the torrent
    absolute_path: str    # where it lands on disk
    size: int
    first_piece: int
    last_piece: int
    head_have: int        # head pieces already downloaded
    head_total: int
    tail_have: int        # tail pieces already downloaded
    tail_total: int
    sequential: bool      # is the torrent in sequential mode

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
