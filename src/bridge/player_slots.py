"""Slots for the in-app video player.

`player.window` is imported inside `playInApp` rather than at module scope. That
import chain ends at libvlc, so hoisting it would make a missing VLC break app
startup instead of just this one feature.
"""

from __future__ import annotations

import json

from PyQt6.QtCore import pyqtSlot

import player
import torrents
from utils.logger import setup_logger

logger = setup_logger("bridge.player")


class PlayerMixin:
    """Mixin providing in-app playback slots."""

    @pyqtSlot(result=str)
    def getPlayerStatus(self) -> str:
        """Whether playback is possible, and why not when it isn't."""
        try:
            return json.dumps(player.describe())
        except Exception as exc:
            logger.error(f"getPlayerStatus failed: {exc}")
            return json.dumps({"available": False, "reason": str(exc)})

    @pyqtSlot(str, result=int)
    def getPlayableFile(self, info_hash: str) -> int:
        """Index of the file a play control would open, or -1 if there is none.

        Read-only: the UI calls it to decide whether to show the control.
        """
        try:
            index = torrents.playable_file(self.session, info_hash)
        except Exception as exc:
            logger.error(f"getPlayableFile failed: {exc}")
            return -1
        return -1 if index is None else index

    @pyqtSlot(str, int, result=str)
    def playInApp(self, info_hash: str, file_index: int = -1) -> str:
        """Reorder pieces for playback and open the player. Returns status JSON.

        Playback starts immediately rather than waiting for the buffer: VLC
        copes with a short file, and the window shows buffering progress. '{}'
        means nothing was opened and a toast explains why.
        """
        if not player.is_available():
            reason = player.describe().get("reason") or "VLC is not available"
            self.toast.emit("error", reason)
            return "{}"

        try:
            status = torrents.start_stream(
                self.session, info_hash, None if file_index < 0 else file_index
            )
        except Exception as exc:
            logger.exception("playInApp could not start the stream")
            self.toast.emit("error", f"Could not prepare stream: {exc}")
            return "{}"
        if status is None:
            self.toast.emit("error", "Nothing playable in this torrent yet")
            return "{}"

        try:
            self._open_player_window(status)
        except Exception as exc:
            logger.exception("playInApp could not open the player")
            self.toast.emit("error", f"Could not open the player: {exc}")
            return "{}"

        return json.dumps(status.to_dict())

    @pyqtSlot()
    def closePlayer(self) -> None:
        window = getattr(self, "_player_window", None)
        if window is not None:
            window.close()

    # ----- Internals ------------------------------------------------------

    def _open_player_window(self, status) -> None:
        from player.backend import VlcPlayer
        from player.window import PlayerWindow

        # One window at a time: opening a second file replaces the first.
        self.closePlayer()

        info_hash = status.info_hash

        def probe() -> dict:
            live = torrents.stream_status(self.session, info_hash)
            return live.to_dict() if live else {}

        def on_close() -> None:
            self._player_window = None
            try:
                torrents.stop_stream(self.session, info_hash)
            except Exception as exc:
                logger.error(f"Could not leave sequential mode for {info_hash}: {exc}")

        window = PlayerWindow(VlcPlayer(), buffer_probe=probe, on_close=on_close)
        window.open(status.absolute_path, title=status.path)
        self._player_window = window
