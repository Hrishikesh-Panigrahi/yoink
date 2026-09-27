from __future__ import annotations

import json

from PyQt6.QtCore import pyqtSlot

import player
import torrents
from utils.logger import setup_logger
from workers import StreamPrepareWorker

logger = setup_logger("bridge.player")


class PlayerMixin:
    @pyqtSlot(result=str)
    def getPlayerStatus(self) -> str:
        """Whether playback works, and why not if it doesn't. Shape: `player.describe()`."""
        try:
            return json.dumps(player.describe())
        except Exception as exc:
            logger.error(f"getPlayerStatus failed: {exc}")
            return json.dumps({"available": False, "reason": str(exc)})

    @pyqtSlot(str, result=int)
    def getPlayableFile(self, info_hash: str) -> int:
        """Index of the file a play button would open, or -1. Changes nothing."""
        try:
            index = torrents.playable_file(self.session, info_hash)
        except Exception as exc:
            logger.error(f"getPlayableFile failed: {exc}")
            return -1
        return -1 if index is None else index

    @pyqtSlot(str, int, result=str)
    def playInApp(self, info_hash: str, file_index: int = -1) -> str:
        """Reorder pieces for playback and open the player. Returns stream status JSON.

        The player opens without waiting for the buffer. VLC copes with a short
        file and the window shows buffering progress. '{}' means nothing opened,
        and a toast says why.
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
        """Add a magnet and open the player once the start of the file has arrived.

        Used from search results. `StreamPrepareWorker` waits for the metadata
        and the first pieces, reports on `streamProgress`, and the window opens
        by itself when it is done.
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
        worker = getattr(self, "_stream_worker", None)
        if worker is not None and worker.isRunning():
            worker.stop()
            worker.requestInterruption()

    @pyqtSlot()
    def closePlayer(self) -> None:
        window = getattr(self, "_player_window", None)
        if window is not None:
            window.close()

    def _start_stream_prepare(self, info_hash: str) -> None:
        self.cancelStreamPrepare()
        self._retire_worker(getattr(self, "_stream_worker", None))

        worker = StreamPrepareWorker(self.session, info_hash)
        worker.progress.connect(self.streamProgress)
        worker.ready.connect(self._on_stream_ready)
        worker.failed.connect(self._on_stream_failed)
        worker.start()
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
        # Imported here because these load libvlc. A missing VLC should break
        # only the player, not app startup.
        from player.backend import VlcPlayer
        from player.window import PlayerWindow

        # One player window at a time: a new file replaces the old one.
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
        # The full size comes from the torrent, so the player waits for missing
        # bytes instead of stopping at the current end of the file.
        window.open(status.absolute_path, title=status.path, expected_size=status.size)
        self._player_window = window
