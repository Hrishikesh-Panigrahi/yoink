"""A thin wrapper over libvlc's MediaPlayer.

It stays free of Qt so it can be tested without a real video surface. It only
knows a window handle and a file path.

The file is usually still downloading. Seeking past the downloaded part stalls
until those pieces arrive, and this layer cannot avoid that.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from player.runtime import load_vlc
from player.source import GrowingFile, build_media, is_incomplete
from utils.logger import setup_logger

logger = setup_logger("player.backend")

#: The large caches smooth over gaps in a file that is still downloading. The
#: other flags keep VLC quiet.
INSTANCE_ARGS = (
    "--no-video-title-show",
    "--no-snapshot-preview",
    "--quiet",
    "--file-caching=5000",
    "--network-caching=5000",
)

UNKNOWN_STATE = "unavailable"


class PlayerUnavailable(RuntimeError):
    """Raised when libvlc could not be loaded."""


class VlcPlayer:
    """One libvlc instance plus one media player."""

    def __init__(self) -> None:
        module, error = load_vlc()
        if module is None:
            raise PlayerUnavailable(error or "VLC is not available")
        self._vlc = module
        self._instance = module.Instance(list(INSTANCE_ARGS))
        if self._instance is None:
            raise PlayerUnavailable("VLC refused to start with the requested options")
        self._player = self._instance.media_player_new()
        self._media = None
        self._path = ""
        self._source: Optional[GrowingFile] = None

    def attach(self, window_handle: int) -> None:
        """Render into a native window. Call before `play`."""
        handle = int(window_handle)
        if sys.platform == "win32":
            self._player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self._player.set_nsobject(handle)
        else:
            self._player.set_xwindow(handle)

    def play(self, path: str = "", expected_size: int = 0) -> bool:
        """Start or resume playback, loading `path` first if it is new.

        `expected_size` is the file's final length. If the file on disk is
        shorter, it is fed through `GrowingFile` so playback waits for the
        missing bytes instead of ending at the current end of the file.
        """
        if path and path != self._path:
            self._load(path, expected_size)
        return self._player.play() == 0

    def _load(self, path: str, expected_size: int) -> None:
        self._release_source()
        if is_incomplete(path, expected_size):
            logger.info(
                f"Streaming {path} through growing-file callbacks "
                f"({os.path.getsize(path)} of {expected_size} bytes present)"
            )
            self._source = GrowingFile(path, expected_size)
            self._media = build_media(self._vlc, self._instance, self._source)
        else:
            self._media = self._instance.media_new_path(path)
        self._player.set_media(self._media)
        self._path = path

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        # Cancel the source first. A read blocked waiting for bytes would
        # otherwise keep libvlc_media_player_stop from returning.
        self._release_source()
        self._player.stop()

    def _release_source(self) -> None:
        if self._source is not None:
            self._source.cancel()
            self._source = None

    def release(self) -> None:
        """Tear down libvlc's objects. Safe to call more than once."""
        self._release_source()
        for name in ("_player", "_media", "_instance"):
            obj = getattr(self, name, None)
            if obj is None:
                continue
            try:
                obj.release()
            except Exception as exc:
                logger.debug(f"{name}.release() failed: {exc}")
            setattr(self, name, None)

    @property
    def path(self) -> str:
        return self._path

    def is_playing(self) -> bool:
        return bool(self._player and self._player.is_playing())

    def time_ms(self) -> int:
        """Playback position. -1 while nothing is loaded."""
        return int(self._player.get_time()) if self._player else -1

    def duration_ms(self) -> int:
        """The length VLC can see so far. It may grow as the file downloads."""
        return int(self._player.get_length()) if self._player else -1

    def seek_ms(self, milliseconds: int) -> None:
        self._player.set_time(max(0, int(milliseconds)))

    def set_volume(self, volume: int) -> None:
        self._player.audio_set_volume(clamp_volume(volume))

    def volume(self) -> int:
        return int(self._player.audio_get_volume()) if self._player else 0

    def state(self) -> str:
        """VLC's state as a plain lowercase string (`playing`, `ended`, ...)."""
        if not self._player:
            return UNKNOWN_STATE
        try:
            return str(self._player.get_state()).rsplit(".", 1)[-1].lower()
        except Exception as exc:
            logger.debug(f"get_state failed: {exc}")
            return UNKNOWN_STATE


def clamp_volume(volume: int) -> int:
    """libvlc silently ignores values outside 0-100, so clamp before passing one."""
    try:
        return max(0, min(100, int(volume)))
    except (TypeError, ValueError):
        return 0
