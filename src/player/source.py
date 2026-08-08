"""Feeding libvlc from a file that is still being written.

VLC's ordinary file access reports end-of-stream the moment it reaches the last
byte on disk. For a torrent that is still downloading this ends playback early
and permanently — measured at 25% of a file, VLC played exactly that 25% and
stopped, while the file went on growing underneath it.

`libvlc_media_new_callbacks` replaces the access module with our own read/seek
pair, and libvlc's own documentation spells out the fix: "if no data is
immediately available, then the callback should sleep". So `read` blocks at the
current end of the file and retries until the missing bytes land.

The same documentation carries the matching warning — the callback must return
an error when playback is stopped, or `libvlc_media_player_stop` never returns
and the UI thread wedges on close. Hence `cancel()`, and hence the stall
timeout: a torrent can simply stop making progress, and a reader that waits
forever is a hang, not a feature.

The torrent's file size is known up front, which is what makes this workable —
it is handed to VLC as the real stream length, so duration and seeking behave
even though most of the bytes have yet to arrive.
"""

from __future__ import annotations

import ctypes
import os
import threading
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("player.source")

#: How long to sleep between checks for newly written bytes.
POLL_SECONDS = 0.1

#: Give up waiting after this long without the file growing. Reported to VLC as
#: end-of-stream, which surfaces as playback stopping rather than a frozen UI.
STALL_TIMEOUT_SECONDS = 30.0

#: libvlc's contract for the read callback.
_END_OF_STREAM = 0
_READ_ERROR = -1


class GrowingFile:
    """A libvlc bitstream source backed by a file that is still downloading.

    One instance serves one playback session. The callback objects are held on
    the instance because ctypes does not keep its own reference — letting them
    be collected while libvlc still holds the pointers crashes the process.
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
        self.waits = 0  # how many times a read had to wait; useful in tests

    # ----- Public -----------------------------------------------------

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

    # ----- libvlc callbacks -------------------------------------------

    def open(self, _opaque, datap, sizep) -> int:
        """Report the *final* size, not what has arrived, so seeking works."""
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
        """Seeking past the downloaded region is allowed; the read then waits."""
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

    # ----- Internals --------------------------------------------------

    def _wait_for_data(self) -> int:
        """Bytes readable at the current position. 0 at EOF, -1 when cancelled.

        Blocks while the file is merely incomplete, which is the whole point.
        """
        waited = 0.0
        while True:
            if self._cancelled.is_set():
                return _READ_ERROR
            ready = self.available() - self._position
            if ready > 0:
                return ready
            if self._position >= self.expected_size:
                return _END_OF_STREAM  # genuinely the end of the file
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


# python-vlc exports `MediaOpenCb` and friends as plain `c_void_p` subclasses —
# the real CFUNCTYPE prototypes live in a scope it never exports, so calling
# `vlc.MediaOpenCb(fn)` raises "cannot be converted to pointer". These mirror
# libvlc's actual signatures; the thunks are cast to the types the binding
# declares as its argtypes.
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

    Both the thunks and their casts are stashed on the source. libvlc keeps raw
    pointers to them for the life of playback, and the cast only carries an
    address — letting either be collected mid-playback kills the process.
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
    """True when the file on disk is shorter than the torrent says it will be."""
    if not expected_size or expected_size <= 0:
        return False
    try:
        return os.path.getsize(path) < expected_size
    except OSError:
        return False
