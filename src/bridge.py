"""Python <-> JavaScript bridge for the embedded web UI.

Exposes a small set of `@pyqtSlot` methods to JS through QWebChannel and
emits signals when torrent state changes. All real work happens in the
`torrents`, `search`, and `db` modules — this class is a thin facade.
"""

from __future__ import annotations

import json
import os
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QFileDialog

import db
import torrents
from providers import site_configs
from search.dto import SearchOptions
from torrents.persistence import load_saved
from torrents.session import Session
from utils.logger import setup_logger
from workers import DownloadsPollWorker, NetworkSpeedWorker, SearchWorker

logger = setup_logger("bridge")


class Bridge(QObject):
    """The single QObject registered as `bridge` on the JS side."""

    downloadsUpdated = pyqtSignal(str)
    networkSpeed = pyqtSignal(float, float)
    searchCompleted = pyqtSignal(str)
    searchError = pyqtSignal(str)
    saveFolderChanged = pyqtSignal(str)
    toast = pyqtSignal(str, str)
    settingsChanged = pyqtSignal(str)
    requestNotification = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        logger.info("Initializing Bridge")

        db.init_db()
        self.save_folder = self._load_save_folder()
        self.session: Session = torrents.create_session(self.save_folder)
        load_saved(self.session)

        self._search_worker: Optional[SearchWorker] = None
        self._completion_announced: set[str] = set()

        self.downloads_worker = DownloadsPollWorker(self.session)
        self.downloads_worker.snapshot.connect(self._on_downloads_snapshot)
        self.downloads_worker.start()

        self.network_worker = NetworkSpeedWorker(self.session)
        self.network_worker.speed.connect(self.networkSpeed)
        self.network_worker.start()

    def _load_save_folder(self) -> str:
        saved = db.get_setting("download_directory")
        if saved and os.path.isdir(saved):
            return saved
        return str(Path.home() / "Downloads")

    def _notifications_enabled(self) -> bool:
        return (db.get_setting("notifications_enabled") or "1") == "1"

    def _on_downloads_snapshot(self, payload: list) -> None:
        self.downloadsUpdated.emit(json.dumps(payload))
        if not self._notifications_enabled():
            return
        for item in payload:
            info_hash = item.get("hash")
            progress = item.get("progress") or 0
            status = (item.get("status") or "").lower()
            if not info_hash or progress < 100:
                continue
            if not any(token in status for token in ("seed", "finish", "complete")):
                continue
            if info_hash in self._completion_announced:
                continue
            self._completion_announced.add(info_hash)
            self.requestNotification.emit("Download complete", item.get("name") or "Torrent")

    @pyqtSlot(str, int, str)
    def search(self, query: str, page: int, options_json: str = "{}") -> None:
        """Kick off an async search; results arrive via `searchCompleted`."""
        query = (query or "").strip()
        if not query:
            self.searchError.emit("Please enter a search query.")
            return

        try:
            raw_options = json.loads(options_json or "{}")
            if not isinstance(raw_options, dict):
                raw_options = {}
        except json.JSONDecodeError:
            raw_options = {}

        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.requestInterruption()

        options = SearchOptions.from_dict(raw_options)
        self._search_worker = SearchWorker(query, max(1, page or 1), options)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.start()
        logger.info(f"Search started: query={query!r} page={page} mode={options.provider_mode.value}")

    def _on_search_finished(self, query: str, page: int, results: list, total: int, pages: int) -> None:
        self.searchCompleted.emit(
            json.dumps({"query": query, "page": page, "results": results, "total": total, "pages": pages})
        )

    def _on_search_failed(self, query: str, error: str) -> None:
        self.searchError.emit(error)

    @pyqtSlot(result=str)
    def getSiteConfigs(self) -> str:
        """Return provider metadata for the web UI."""
        try:
            return json.dumps(site_configs())
        except Exception as exc:
            logger.error(f"getSiteConfigs failed: {exc}")
            return "{}"

    @pyqtSlot(result=str)
    def getDownloads(self) -> str:
        """Return a snapshot of current downloads as JSON."""
        try:
            payload = [s.to_dict() for s in torrents.list_torrents(self.session)]
            return json.dumps(payload)
        except Exception as exc:
            logger.error(f"getDownloads error: {exc}")
            return "[]"

    @pyqtSlot(str, result=str)
    def addTorrent(self, magnet: str) -> str:
        """Add a torrent from a magnet link. Returns info hash or empty string."""
        magnet = (magnet or "").strip()
        if not magnet:
            self.toast.emit("error", "No magnet link provided")
            return ""
        try:
            torrents.set_save_path(self.session, self.save_folder)
            info_hash = torrents.add_magnet(self.session, magnet)
            self.toast.emit("success", "Torrent added")
            return info_hash
        except Exception as exc:
            logger.exception("addTorrent failed")
            self.toast.emit("error", f"Failed to add torrent: {exc}")
            return ""

    @pyqtSlot(result=str)
    def pickAndAddTorrentFile(self) -> str:
        """Open a native file picker and add the selected .torrent file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Select Torrent File",
                self.save_folder,
                "Torrent Files (*.torrent);;All Files (*)",
            )
            if not file_path:
                return ""
            torrents.set_save_path(self.session, self.save_folder)
            info_hash = torrents.add_torrent_file(self.session, file_path)
            self.toast.emit("success", f"Added: {os.path.basename(file_path)}")
            return info_hash
        except Exception as exc:
            logger.exception("pickAndAddTorrentFile failed")
            self.toast.emit("error", str(exc))
            return ""

    @pyqtSlot(str, result=bool)
    def pauseTorrent(self, info_hash: str) -> bool:
        try:
            return torrents.pause(self.session, info_hash)
        except Exception as exc:
            logger.exception("pauseTorrent failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(str, result=bool)
    def resumeTorrent(self, info_hash: str) -> bool:
        try:
            return torrents.resume(self.session, info_hash)
        except Exception as exc:
            logger.exception("resumeTorrent failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(str, bool, result=bool)
    def removeTorrent(self, info_hash: str, delete_files: bool) -> bool:
        try:
            ok = torrents.remove(self.session, info_hash, delete_files)
            if ok:
                self.toast.emit("success", "Removed")
            return ok
        except Exception as exc:
            logger.exception("removeTorrent failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(result=str)
    def getSaveFolder(self) -> str:
        return self.save_folder

    @pyqtSlot(result=str)
    def pickSaveFolder(self) -> str:
        """Show a directory picker; persist and return the new folder."""
        try:
            new_dir = QFileDialog.getExistingDirectory(
                None,
                "Select Download Folder",
                self.save_folder,
                QFileDialog.Option.ShowDirsOnly,
            )
            if not new_dir:
                return self.save_folder
            self.save_folder = new_dir
            torrents.set_save_path(self.session, new_dir)
            db.set_setting("download_directory", new_dir)
            self.saveFolderChanged.emit(new_dir)
            self.toast.emit("success", f"Save folder set to {new_dir}")
            return new_dir
        except Exception as exc:
            logger.exception("pickSaveFolder failed")
            self.toast.emit("error", str(exc))
            return self.save_folder

    @pyqtSlot(str)
    def openSaveFolder(self, path: str = "") -> None:
        """Open a folder in the OS file explorer."""
        target = path or self.save_folder
        try:
            os.startfile(target)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.error(f"openSaveFolder failed: {exc}")
            self.toast.emit("error", f"Cannot open folder: {exc}")

    @pyqtSlot(str)
    def openExternal(self, url: str) -> None:
        """Open a URL in the user's default browser."""
        try:
            webbrowser.open(url)
        except Exception as exc:
            logger.error(f"openExternal failed: {exc}")
            self.toast.emit("error", f"Cannot open link: {exc}")

    @pyqtSlot(result=str)
    def getSettings(self) -> str:
        """Return the current persisted settings as JSON."""
        return json.dumps(self._settings_dict())

    def _settings_dict(self) -> dict:
        def _bool_setting(key: str, default: str = "1") -> bool:
            return (db.get_setting(key) or default) == "1"

        return {
            "saveFolder": self.save_folder,
            "notifications": _bool_setting("notifications_enabled"),
            "minimizeToTray": _bool_setting("minimize_to_tray"),
        }

    @pyqtSlot(str, bool)
    def setBoolSetting(self, key: str, value: bool) -> None:
        """Persist a boolean setting and notify listeners."""
        db.set_setting(key, "1" if value else "0")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str, str, str)
    def notify(self, kind: str, title: str, message: str) -> None:
        """Trigger a native tray notification if enabled."""
        if not self._notifications_enabled():
            return
        self.requestNotification.emit(title or "Yoink", message or "")

    def minimize_to_tray_enabled(self) -> bool:
        return (db.get_setting("minimize_to_tray") or "1") == "1"

    def shutdown(self) -> None:
        """Stop workers and the libtorrent session before quitting."""
        logger.info("Bridge shutting down")
        for worker_name in ("downloads_worker", "network_worker"):
            worker = getattr(self, worker_name, None)
            if worker is None:
                continue
            try:
                worker.stop()
                worker.wait(2000)
            except Exception as exc:
                logger.error(f"{worker_name} shutdown error: {exc}")

        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.requestInterruption()
            self._search_worker.wait(1000)

        try:
            torrents.stop_session(self.session)
        except Exception as exc:
            logger.error(f"Session shutdown error: {exc}")
