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
from workers import StreamPrepareWorker

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

    @pyqtSlot(str, result=str)
    def playFromMagnet(self, magnet: str) -> str:
        """Add a magnet and play it as soon as enough of the file has arrived.

        This is the search-result path. Unlike `playInApp`, nothing is known
        about the torrent yet: the magnet has to be added, the file list waited
        for, and the head buffered before a player can open anything. All three
        happen on `StreamPrepareWorker`; progress arrives on `streamProgress`
        and the window opens by itself when the head is in.
        """
        if not player.is_available():
            reason = player.describe().get("reason") or "VLC is not available"
            self.toast.emit("error", reason)
            return "{}"

        magnet = (magnet or "").strip()
        if not magnet:
            self.toast.emit("error", "No magnet link on this result")
            return "{}"

        try:
            torrents.set_save_path(self.session, self.save_folder)
            info_hash, was_existing = torrents.add_magnet_verbose(self.session, magnet)
        except Exception as exc:
            logger.exception("playFromMagnet could not add the magnet")
            self.toast.emit("error", f"Could not add torrent: {exc}")
            return "{}"

        self._start_stream_prepare(info_hash)
        return json.dumps({"hash": info_hash, "wasExisting": was_existing})

    @pyqtSlot()
    def cancelStreamPrepare(self) -> None:
        """Stop waiting for a stream that the user no longer wants."""
        worker = getattr(self, "_stream_worker", None)
        if worker is not None and worker.isRunning():
            worker.stop()
            worker.requestInterruption()

    @pyqtSlot()
    def closePlayer(self) -> None:
        window = getattr(self, "_player_window", None)
        if window is not None:
            window.close()

    # ----- Internals ------------------------------------------------------

    def _start_stream_prepare(self, info_hash: str) -> None:
        """Wait for metadata and the head, then open the player."""
        self.cancelStreamPrepare()
        self._retire_worker(getattr(self, "_stream_worker", None))

        worker = StreamPrepareWorker(self.session, info_hash)
        worker.progress.connect(self.streamProgress)
        worker.ready.connect(self._on_stream_ready)
        worker.failed.connect(self._on_stream_failed)
        worker.start()
        # Held on the bridge: dropping the last reference to a running QThread
        # lets it be collected mid-run.
        self._stream_worker = worker

    def _on_stream_ready(self, info_hash: str, file_index: int) -> None:
        status = torrents.stream_status(self.session, info_hash)
        if status is None:
            self.toast.emit("error", "The stream disappeared before it could play")
            return
        try:
            self._open_player_window(status)
        except Exception as exc:
            logger.exception("Could not open the player for a prepared stream")
            self.toast.emit("error", f"Could not open the player: {exc}")

    def _on_stream_failed(self, info_hash: str, reason: str) -> None:
        logger.warning(f"Stream preparation failed for {info_hash}: {reason}")
        self.toast.emit("error", reason)
        self.streamProgress.emit(
            json.dumps({"hash": info_hash, "phase": "failed", "message": reason})
        )

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
        # The final size comes from the torrent, so the player can wait for
        # bytes that have not arrived rather than stopping at the current EOF.
        window.open(status.absolute_path, title=status.path, expected_size=status.size)
        self._player_window = window
