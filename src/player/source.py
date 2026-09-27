"""Feed libvlc from a file that is still being written.

VLC's normal file access treats the last byte on disk as the end of the stream,
so a partly downloaded file stops playing early and never picks up again.
`libvlc_media_new_callbacks` lets us supply our own read and seek. libvlc's docs
say a read with no data available should sleep, so `read` waits at the current
end of the file until more bytes arrive.

libvlc also needs the read to return an error once playback stops, or
`libvlc_media_player_stop` never returns and the UI hangs on close. That is what
`cancel()` and the stall timeout are for.

The final size is known from the torrent and reported to VLC as the stream
length, so duration and seeking work before most of the bytes arrive.
"""

from __future__ import annotations

import ctypes
import os
import threading
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("player.source")

POLL_SECONDS = 0.1

#: Give up after this long without new data. VLC is told end-of-stream, so
#: playback stops instead of the UI freezing.
STALL_TIMEOUT_SECONDS = 30.0

#: Return values libvlc expects from the read callback.
_END_OF_STREAM = 0
_READ_ERROR = -1


class GrowingFile:
    """A libvlc media source backed by a file that is still downloading.

    Use one instance per playback.
    """

    def __init__(
        self,
        path: str,
        expected_size: int,
        poll_seconds: float = POLL_SECONDS,
        stall_timeout: float = STALL_TIMEOUT_SECONDS,
    ) -> None:
        self.path = path
        self.expected_size = int(expected_size)
        self.poll_seconds = poll_seconds
        self.stall_timeout = stall_timeout
        self._position = 0
        self._cancelled = threading.Event()
        self._handle: Optional[object] = None
        self.waits = 0  # counts reads that had to wait, for tests

    def cancel(self) -> None:
        """Unblock any waiting read so `stop()` can return."""
        self._cancelled.set()

    @property
    def position(self) -> int:
        return self._position

    def available(self) -> int:
        """Bytes currently on disk."""
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0

    def open(self, _opaque, datap, sizep) -> int:
        """Report the final size so VLC can seek into bytes that have not arrived."""
        try:
            self._position = 0
            self._handle = open(self.path, "rb")
            if datap:
                datap[0] = None
            if sizep:
                sizep[0] = self.expected_size
            return 0
        except Exception as exc:
            logger.error(f"GrowingFile open failed for {self.path}: {exc}")
            return -1

    def read(self, _opaque, buf, length) -> int:
        """Fill `buf`, waiting for bytes that have not been written yet."""
        try:
            ready = self._wait_for_data()
        except Exception as exc:
            logger.error(f"GrowingFile wait failed: {exc}")
            return _READ_ERROR
        if ready <= 0:
            return ready

        want = min(int(length), ready)
        try:
            self._handle.seek(self._position)
            chunk = self._handle.read(want)
        except Exception as exc:
            logger.error(f"GrowingFile read failed at {self._position}: {exc}")
            return _READ_ERROR
        if not chunk:
            return _END_OF_STREAM

        ctypes.memmove(buf, chunk, len(chunk))
        self._position += len(chunk)
        return len(chunk)

    def seek(self, _opaque, offset) -> int:
        """Seeking past the downloaded part is allowed. The next read waits."""
        self._position = max(0, int(offset))
        return 0

    def close(self, _opaque) -> None:
        self.cancel()
        handle, self._handle = self._handle, None
        if handle is not None:
            try:
                handle.close()
            except Exception as exc:
                logger.debug(f"GrowingFile close failed: {exc}")

    def _wait_for_data(self) -> int:
        """Bytes readable at the current position, blocking while none are.

        Returns 0 at end of stream and -1 when cancelled.
        """
        waited = 0.0
        while True:
            if self._cancelled.is_set():
                return _READ_ERROR
            ready = self.available() - self._position
            if ready > 0:
                return ready
            if self._position >= self.expected_size:
                return _END_OF_STREAM
            if waited >= self.stall_timeout:
                logger.warning(
                    f"No new data for {self.stall_timeout:.0f}s at byte "
                    f"{self._position} of {self.expected_size}; ending playback"
                )
                return _END_OF_STREAM
            self.waits += 1
            # Event.wait doubles as the sleep and the cancellation check.
            if self._cancelled.wait(self.poll_seconds):
                return _READ_ERROR
            waited += self.poll_seconds


# python-vlc exposes `MediaOpenCb` and the others as plain `c_void_p` subclasses,
# so `vlc.MediaOpenCb(fn)` fails with "cannot be converted to pointer". These
# prototypes match libvlc's real signatures, and `build_media` casts the thunks
# to the types python-vlc declares.
OPEN_PROTO = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_uint64),
)
READ_PROTO = ctypes.CFUNCTYPE(
    ctypes.c_ssize_t,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_char),
    ctypes.c_size_t,
)
SEEK_PROTO = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint64)
CLOSE_PROTO = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


def build_media(vlc_module, instance, source: GrowingFile):
    """Wrap `source` in a libvlc media object.

    The thunks and their casts are stored on `source` because libvlc keeps raw
    pointers to them during playback. If Python collects either one, the
    process crashes.
    """
    source._thunks = (
        OPEN_PROTO(source.open),
        READ_PROTO(source.read),
        SEEK_PROTO(source.seek),
        CLOSE_PROTO(source.close),
    )
    source._casts = tuple(
        ctypes.cast(thunk, declared)
        for thunk, declared in zip(
            source._thunks,
            (
                vlc_module.MediaOpenCb,
                vlc_module.MediaReadCb,
                vlc_module.MediaSeekCb,
                vlc_module.MediaCloseCb,
            ),
            strict=True,
        )
    )
    return instance.media_new_callbacks(*source._casts, None)


def is_incomplete(path: str, expected_size: int) -> bool:
    """True when the file on disk is shorter than `expected_size`. False if missing."""
    if not expected_size or expected_size <= 0:
        return False
    try:
        return os.path.getsize(path) < expected_size
    except OSError:
        return False
