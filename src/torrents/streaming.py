"""Sequential piece ordering, so a file can be played while it downloads.

libtorrent's default piece picker optimises for the swarm: it asks for the
rarest pieces first, in whatever order they turn up. That is exactly wrong for
playback, which needs byte 0 before byte 1. Two libtorrent features fix it and
this module is the only place either is used:

- ``sequential_download``, a torrent-wide flag that switches the picker to
  in-order requests.
- ``set_piece_deadline``, which promotes individual pieces ahead of the queue.

Both ends of the file are prioritised, not just the front. The head is what a
player reads first. The tail matters because MP4 keeps its ``moov`` index at the
end unless the file was explicitly written for streaming, and Matroska keeps its
cues there — a player that cannot see the tail typically reports an unknown
duration and refuses to seek.

Nothing here decides *how* the file is played. It only makes the bytes arrive in
an order a player can use.
"""

from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

import libtorrent as lt

from torrents.dto import StreamPlan, StreamStatus
from torrents.session import Session
from utils.logger import setup_logger

logger = setup_logger("torrents.streaming")

#: Containers worth offering a "play" control for.
VIDEO_EXTENSIONS = frozenset(
    {
        ".avi", ".flv", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg",
        ".mpg", ".ts", ".webm", ".wmv",
    }
)

#: How much of each end to insist on before calling a file playable. The head is
#: sized to cover a container's header plus a few seconds of video; the tail only
#: has to cover a trailing index.
DEFAULT_HEAD_BYTES = 16 * 1024 * 1024
DEFAULT_TAIL_BYTES = 2 * 1024 * 1024

#: Spacing between the deadlines handed to consecutive head pieces. Deadlines are
#: relative to now, so ascending values keep the head in playback order.
DEADLINE_STEP_MS = 100

#: Tail pieces are wanted early but never ahead of the head.
TAIL_DEADLINE_MS = 30_000


def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS


def pick_video_file(files: Sequence[Tuple[str, int]]) -> Optional[int]:
    """Return the index of the video file a "play" control should target.

    ``files`` is ``(path, size)`` in torrent order. The largest video wins.
    Release groups often ship a short clip under ``sample/``, which is a video by
    every other measure, so those are only considered when nothing else is.
    """
    videos = [(idx, path, size) for idx, (path, size) in enumerate(files) if is_video(path)]
    if not videos:
        return None
    preferred = [entry for entry in videos if not _looks_like_a_sample(entry[1])]
    candidates = preferred or videos
    return max(candidates, key=lambda entry: entry[2])[0]


def _looks_like_a_sample(path: str) -> bool:
    parts = path.replace("\\", "/").lower().split("/")
    return any(part == "sample" for part in parts[:-1]) or parts[-1].startswith("sample")


def plan_stream(
    file_offset: int,
    file_size: int,
    piece_length: int,
    num_pieces: int,
    head_bytes: int = DEFAULT_HEAD_BYTES,
    tail_bytes: int = DEFAULT_TAIL_BYTES,
) -> StreamPlan:
    """Work out which pieces cover the head and tail of one file in a torrent.

    Pure arithmetic on the torrent's layout — no handle, no session — because
    this is the part worth testing exhaustively.
    """
    if piece_length <= 0 or num_pieces <= 0:
        raise ValueError("piece_length and num_pieces must be positive")

    last_index = num_pieces - 1
    first_piece = min(max(file_offset // piece_length, 0), last_index)
    if file_size <= 0:
        return StreamPlan(first_piece, first_piece, (first_piece,), ())
    last_piece = min((file_offset + file_size - 1) // piece_length, last_index)

    head_count = _pieces_for(min(head_bytes, file_size), piece_length)
    head_end = min(first_piece + head_count - 1, last_piece)
    head = tuple(range(first_piece, head_end + 1))

    tail_count = _pieces_for(min(tail_bytes, file_size), piece_length)
    tail_start = max(last_piece - tail_count + 1, first_piece)
    # A short file can make the two windows meet; the head already covers it.
    tail = tuple(piece for piece in range(tail_start, last_piece + 1) if piece > head_end)

    return StreamPlan(first_piece, last_piece, head, tail)


def _pieces_for(byte_count: int, piece_length: int) -> int:
    """Pieces needed to hold `byte_count`, at least one. May straddle a boundary."""
    return max(1, -(-int(byte_count) // piece_length) + 1)


def start_stream(
    session: Session,
    info_hash: str,
    file_index: Optional[int] = None,
    head_bytes: int = DEFAULT_HEAD_BYTES,
    tail_bytes: int = DEFAULT_TAIL_BYTES,
) -> Optional[StreamStatus]:
    """Switch a torrent to sequential order and rush one file's head and tail.

    Returns the resulting status, or None when there is no metadata yet or the
    torrent holds nothing playable. Passing `file_index` overrides the automatic
    pick; anything out of range is treated as "choose for me".
    """
    handle = _live_handle(session, info_hash)
    if handle is None:
        return None

    layout = _layout(handle)
    if layout is None:
        return None
    files, piece_length, num_pieces = layout

    index = _resolve_index(files, file_index)
    if index is None:
        logger.info(f"No playable file in {info_hash}")
        return None

    plan = plan_stream(
        files[index][2], files[index][1], piece_length, num_pieces, head_bytes, tail_bytes
    )

    _set_sequential(handle, True)
    _ensure_wanted(handle, index)
    _apply_deadlines(handle, plan)
    session.streams[info_hash.lower()] = index

    logger.info(
        f"Streaming {info_hash} file {index} "
        f"({len(plan.head_pieces)} head + {len(plan.tail_pieces)} tail pieces)"
    )
    return _status(handle, info_hash.lower(), index, files, plan)


def playable_file(session: Session, info_hash: str) -> Optional[int]:
    """Index of the file a play control would target, without changing anything.

    The UI asks this to decide whether to show the control at all, so it must not
    set flags, deadlines or priorities.
    """
    handle = _live_handle(session, info_hash)
    if handle is None:
        return None
    layout = _layout(handle)
    if layout is None:
        return None
    files = layout[0]
    return pick_video_file([(path, size) for path, size, _ in files])


def stream_status(session: Session, info_hash: str) -> Optional[StreamStatus]:
    """Report progress on the file `start_stream` selected, or None if idle."""
    key = info_hash.lower()
    index = session.streams.get(key)
    if index is None:
        return None
    handle = _live_handle(session, key)
    if handle is None:
        return None
    layout = _layout(handle)
    if layout is None:
        return None
    files, piece_length, num_pieces = layout
    if not 0 <= index < len(files):
        return None

    plan = plan_stream(files[index][2], files[index][1], piece_length, num_pieces)
    return _status(handle, key, index, files, plan)


def stop_stream(session: Session, info_hash: str) -> bool:
    """Drop the deadlines and leave sequential mode. Returns True if it was on."""
    key = info_hash.lower()
    was_streaming = session.streams.pop(key, None) is not None
    handle = _live_handle(session, key)
    if handle is None:
        return was_streaming
    try:
        handle.clear_piece_deadlines()
    except Exception as exc:
        logger.warning(f"clear_piece_deadlines failed for {key}: {exc}")
    _set_sequential(handle, False)
    return was_streaming


# ----- Handle plumbing ----------------------------------------------------


def _live_handle(session: Session, info_hash: str):
    handle = session.handles.get((info_hash or "").lower())
    if handle is None or not handle.is_valid():
        return None
    return handle


def _layout(handle) -> Optional[Tuple[List[Tuple[str, int, int]], int, int]]:
    """Return ((path, size, offset) per file, piece_length, num_pieces)."""
    try:
        if not handle.has_metadata():
            return None
        info = handle.get_torrent_info()
        files = info.files()
        table = [
            (files.file_path(idx), int(files.file_size(idx)), int(files.file_offset(idx)))
            for idx in range(files.num_files())
        ]
        return table, int(info.piece_length()), int(info.num_pieces())
    except Exception as exc:
        logger.error(f"Could not read torrent layout: {exc}")
        return None


def _resolve_index(
    files: Sequence[Tuple[str, int, int]], requested: Optional[int]
) -> Optional[int]:
    if requested is not None and 0 <= requested < len(files):
        return requested
    return pick_video_file([(path, size) for path, size, _ in files])


def _set_sequential(handle, enabled: bool) -> None:
    try:
        if enabled:
            handle.set_flags(lt.torrent_flags.sequential_download)
        else:
            handle.unset_flags(lt.torrent_flags.sequential_download)
    except Exception as exc:
        logger.warning(f"Could not toggle sequential_download: {exc}")


def _ensure_wanted(handle, index: int) -> None:
    """Un-skip the target file. Other files keep whatever the user chose."""
    try:
        if handle.file_priority(index) == 0:
            handle.file_priority(index, 4)
    except Exception as exc:
        logger.warning(f"Could not raise priority of file {index}: {exc}")


def _apply_deadlines(handle, plan: StreamPlan) -> None:
    """Ask for the head in playback order, then the tail."""
    for offset, piece in enumerate(plan.head_pieces):
        _set_deadline(handle, piece, offset * DEADLINE_STEP_MS)
    for offset, piece in enumerate(plan.tail_pieces):
        _set_deadline(handle, piece, TAIL_DEADLINE_MS + offset * DEADLINE_STEP_MS)


def _set_deadline(handle, piece: int, deadline_ms: int) -> None:
    try:
        handle.set_piece_deadline(piece, deadline_ms)
    except Exception as exc:
        logger.debug(f"set_piece_deadline({piece}) failed: {exc}")


def _status(
    handle, info_hash: str, index: int, files: Sequence[Tuple[str, int, int]], plan: StreamPlan
) -> StreamStatus:
    path, size, _offset = files[index]
    try:
        save_path = handle.status().save_path
    except Exception:
        save_path = ""
    return StreamStatus(
        info_hash=info_hash,
        file_index=index,
        path=path,
        absolute_path=os.path.join(save_path, path) if save_path else path,
        size=size,
        first_piece=plan.first_piece,
        last_piece=plan.last_piece,
        head_have=_count_have(handle, plan.head_pieces),
        head_total=len(plan.head_pieces),
        tail_have=_count_have(handle, plan.tail_pieces),
        tail_total=len(plan.tail_pieces),
        sequential=_is_sequential(handle),
    )


def _count_have(handle, pieces: Sequence[int]) -> int:
    try:
        return sum(1 for piece in pieces if handle.have_piece(piece))
    except Exception as exc:
        logger.debug(f"have_piece failed: {exc}")
        return 0


def _is_sequential(handle) -> bool:
    try:
        return bool(handle.flags() & lt.torrent_flags.sequential_download)
    except Exception:
        return False
