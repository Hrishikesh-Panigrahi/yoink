"""A thin wrapper over libvlc's MediaPlayer.

Kept deliberately small and Qt-free: it knows about a window handle and a file
path, nothing about widgets. That keeps the parts worth testing — availability
handling, state mapping, clamping — separable from the parts that need a real
video surface.

Playing a file that is still downloading is the whole point, so the instance is
built with a generous file cache and VLC's own "file is growing" behaviour is
relied on: it reads what exists and reports the length it can see. Seeking past
the downloaded region stalls until those pieces arrive, which is inherent rather
than something this layer can paper over.
"""

from __future__ import annotations

import sys
from typing import Optional

from player.runtime import load_vlc
from utils.logger import setup_logger

logger = setup_logger("player.backend")

#: Passed to libvlc at construction. A large file cache smooths over the gaps a
#: still-downloading file produces; the rest just keeps VLC quiet and headless.
INSTANCE_ARGS = (
    "--no-video-title-show",
    "--no-snapshot-preview",
    "--quiet",
    "--file-caching=5000",
    "--network-caching=5000",
)

#: Reported when the backing library never loaded.
UNKNOWN_STATE = "unavailable"


class PlayerUnavailable(RuntimeError):
    """Raised when a player is asked for but libvlc could not be loaded."""


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

    # ----- Surface --------------------------------------------------------

    def attach(self, window_handle: int) -> None:
        """Render into a native window. Call before `play`."""
        handle = int(window_handle)
        if sys.platform == "win32":
            self._player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self._player.set_nsobject(handle)
        else:
            self._player.set_xwindow(handle)

    # ----- Transport ------------------------------------------------------

    def play(self, path: str = "") -> bool:
        """Start (or resume) playback. Passing a path loads it first."""
        if path and path != self._path:
            self._media = self._instance.media_new_path(path)
            self._player.set_media(self._media)
            self._path = path
        return self._player.play() == 0

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def release(self) -> None:
        """Tear down libvlc's objects. Safe to call more than once."""
        for name in ("_player", "_media", "_instance"):
            obj = getattr(self, name, None)
            if obj is None:
                continue
            try:
                obj.release()
            except Exception as exc:
                logger.debug(f"{name}.release() failed: {exc}")
            setattr(self, name, None)

    # ----- Position and volume -------------------------------------------

    @property
    def path(self) -> str:
        return self._path

    def is_playing(self) -> bool:
        return bool(self._player and self._player.is_playing())

    def time_ms(self) -> int:
        """Where playback is now. -1 while nothing is loaded."""
        return int(self._player.get_time()) if self._player else -1

    def duration_ms(self) -> int:
        """What VLC can currently see. Grows as more of the file lands."""
        return int(self._player.get_length()) if self._player else -1

    def seek_ms(self, milliseconds: int) -> None:
        self._player.set_time(max(0, int(milliseconds)))

    def set_volume(self, volume: int) -> None:
        self._player.audio_set_volume(clamp_volume(volume))

    def volume(self) -> int:
        return int(self._player.audio_get_volume()) if self._player else 0

    def set_muted(self, muted: bool) -> None:
        self._player.audio_set_mute(bool(muted))

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
    """libvlc accepts 0-100; anything else is silently ignored, so clamp here."""
    try:
        return max(0, min(100, int(volume)))
    except (TypeError, ValueError):
        return 0


def create_player() -> Optional[VlcPlayer]:
    """Build a player, or return None with the reason logged."""
    try:
        return VlcPlayer()
    except PlayerUnavailable as exc:
        logger.warning(f"Player unavailable: {exc}")
        return None
