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
from providers import all_provider_choices, site_configs
from search.dto import SearchOptions
from torrents.persistence import load_saved
from torrents.session import Session
from utils import autostart
from utils.logger import setup_logger
from version import __app_homepage__, __version__
from workers import (
    DownloadsPollWorker,
    MetadataEnrichWorker,
    NetworkSpeedWorker,
    ProviderHealthWorker,
    SearchWorker,
    UpdateCheckWorker,
)

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
    metadataEnriched = pyqtSignal(str, str)  # query, JSON list of {key, metadata}
    providerHealth = pyqtSignal(str)  # JSON map of provider key -> status dict
    updateAvailable = pyqtSignal(str)  # JSON dict; "{}" when none

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        logger.info("Initializing Bridge")

        db.init_db()
        self.save_folder = self._load_save_folder()
        self.session: Session = torrents.create_session(self.save_folder)
        load_saved(self.session)
        self._apply_session_limits_from_db()

        self._search_worker: Optional[SearchWorker] = None
        self._metadata_worker: Optional[MetadataEnrichWorker] = None
        self._health_worker: Optional[ProviderHealthWorker] = None
        self._update_worker: Optional[UpdateCheckWorker] = None
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
        ratio = self._float_setting("seed_ratio_limit", 0.0)
        if ratio > 0:
            torrents.enforce_seed_ratio(self.session, ratio)
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

        raw_options = self._apply_enabled_providers(raw_options)

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
        self._kick_metadata_enrich(query, results)

    def _kick_metadata_enrich(self, query: str, results: list) -> None:
        """Fire off TMDB enrichment for the visible page."""
        if self._metadata_worker and self._metadata_worker.isRunning():
            self._metadata_worker.requestInterruption()
        worker = MetadataEnrichWorker(query, results)
        worker.enriched.connect(self._on_metadata_enriched)
        worker.start()
        self._metadata_worker = worker

    def _on_metadata_enriched(self, query: str, updates: list) -> None:
        try:
            self.metadataEnriched.emit(query, json.dumps(updates))
        except Exception as exc:
            logger.error(f"metadataEnriched emit failed: {exc}")

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
    def getProviderChoices(self) -> str:
        """List every toggleable provider with current enabled state."""
        try:
            choices = all_provider_choices()
            enabled = self._enabled_provider_set()
            for choice in choices:
                choice["enabled"] = choice["key"] in enabled
            return json.dumps(choices)
        except Exception as exc:
            logger.error(f"getProviderChoices failed: {exc}")
            return "[]"

    @pyqtSlot()
    def refreshProviderHealth(self) -> None:
        """Probe every provider and emit `providerHealth` when done."""
        if self._health_worker and self._health_worker.isRunning():
            return
        worker = ProviderHealthWorker()
        worker.finished.connect(lambda statuses: self.providerHealth.emit(json.dumps(statuses)))
        worker.start()
        self._health_worker = worker

    @pyqtSlot(str, bool)
    def setProviderEnabled(self, key: str, enabled: bool) -> None:
        """Toggle a provider on/off and persist the choice."""
        current = self._enabled_provider_set()
        if enabled:
            current.add(key)
        else:
            current.discard(key)
        db.set_setting("enabled_providers", ",".join(sorted(current)))
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    def _enabled_provider_set(self) -> set[str]:
        raw = db.get_setting("enabled_providers")
        if raw is None:
            return {choice["key"] for choice in all_provider_choices() if choice["defaultOn"]}
        return {part.strip() for part in raw.split(",") if part.strip()}

    def _apply_enabled_providers(self, options: dict) -> dict:
        """Inject enabled-provider config into the per-search options blob."""
        enabled = self._enabled_provider_set()
        stable_keys = {"yts", "piratebay_stable"}
        enabled_stable = sorted(enabled & stable_keys)
        enabled_vendor = sorted(
            key.split(":", 1)[1] for key in enabled if key.startswith("vendor:")
        )
        merged = dict(options)
        merged["enabledStable"] = enabled_stable
        if not merged.get("sites") and enabled_vendor:
            # In MULTI mode, default the site list to the user's selection.
            merged.setdefault("sites", enabled_vendor)
        return merged

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

    @pyqtSlot(result=int)
    def pauseAll(self) -> int:
        """Pause every torrent. Returns how many were paused."""
        try:
            count = torrents.pause_all(self.session)
            if count:
                self.toast.emit("success", f"Paused {count} torrent{'s' if count != 1 else ''}")
            return count
        except Exception as exc:
            logger.exception("pauseAll failed")
            self.toast.emit("error", str(exc))
            return 0

    @pyqtSlot(result=int)
    def resumeAll(self) -> int:
        """Resume every torrent. Returns how many were resumed."""
        try:
            count = torrents.resume_all(self.session)
            if count:
                self.toast.emit("success", f"Resumed {count} torrent{'s' if count != 1 else ''}")
            return count
        except Exception as exc:
            logger.exception("resumeAll failed")
            self.toast.emit("error", str(exc))
            return 0

    @pyqtSlot(str, result=str)
    def getTorrentFiles(self, info_hash: str) -> str:
        """Return the per-file table for a torrent (empty list while metadata loads)."""
        try:
            files = torrents.list_files(self.session, info_hash)
            return json.dumps([f.to_dict() for f in files])
        except Exception as exc:
            logger.error(f"getTorrentFiles failed: {exc}")
            return "[]"

    @pyqtSlot(str, str, result=bool)
    def setFilePriorities(self, info_hash: str, priorities_json: str) -> bool:
        """Apply a {index: priority} map. Priority: 0=skip, 1=low, 4=normal, 7=high."""
        try:
            payload = json.loads(priorities_json or "{}")
            if not isinstance(payload, dict):
                return False
            ok = torrents.set_file_priorities(self.session, info_hash, payload)
            if ok:
                self.toast.emit("success", "File selection updated")
            return ok
        except Exception as exc:
            logger.exception("setFilePriorities failed")
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
            "launchAtLogin": autostart.is_enabled(),
            "downloadLimitKbS": self._int_setting("download_limit_kb_s", 0),
            "uploadLimitKbS": self._int_setting("upload_limit_kb_s", 0),
            "maxActiveDownloads": self._int_setting("max_active_downloads", 0),
            "maxActiveSeeds": self._int_setting("max_active_seeds", 0),
            "seedRatioLimit": self._float_setting("seed_ratio_limit", 0.0),
            "tmdbConfigured": bool(db.get_setting("tmdb_api_key")),
        }

    def _int_setting(self, key: str, default: int = 0) -> int:
        try:
            return int(db.get_setting(key) or default)
        except (TypeError, ValueError):
            return default

    def _float_setting(self, key: str, default: float = 0.0) -> float:
        try:
            return float(db.get_setting(key) or default)
        except (TypeError, ValueError):
            return default

    def _apply_session_limits_from_db(self) -> None:
        torrents.apply_limits(
            self.session,
            download_kb_s=self._int_setting("download_limit_kb_s", 0),
            upload_kb_s=self._int_setting("upload_limit_kb_s", 0),
            active_downloads=self._int_setting("max_active_downloads", 0),
            active_seeds=self._int_setting("max_active_seeds", 0),
        )

    @pyqtSlot(str, bool)
    def setBoolSetting(self, key: str, value: bool) -> None:
        """Persist a boolean setting and notify listeners."""
        db.set_setting(key, "1" if value else "0")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str, int)
    def setIntSetting(self, key: str, value: int) -> None:
        """Persist an int setting (bandwidth caps, active limits)."""
        db.set_setting(key, str(int(value)))
        if key in {"download_limit_kb_s", "upload_limit_kb_s", "max_active_downloads", "max_active_seeds"}:
            self._apply_session_limits_from_db()
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str, float)
    def setFloatSetting(self, key: str, value: float) -> None:
        """Persist a float setting (e.g. seed_ratio_limit)."""
        db.set_setting(key, f"{float(value):.4f}")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot()
    def checkForUpdates(self) -> None:
        """Async update check; result lands on `updateAvailable`."""
        if self._update_worker and self._update_worker.isRunning():
            return
        worker = UpdateCheckWorker()
        worker.finished.connect(self._on_update_check)
        worker.start()
        self._update_worker = worker

    def _on_update_check(self, payload) -> None:
        try:
            self.updateAvailable.emit(json.dumps(payload or {}))
        except Exception as exc:
            logger.error(f"updateAvailable emit failed: {exc}")

    @pyqtSlot(result=str)
    def getAboutInfo(self) -> str:
        """Return version/homepage info shown in the About panel."""
        import platform
        return json.dumps({
            "version": __version__,
            "homepage": __app_homepage__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        })

    @pyqtSlot(str)
    def setTmdbApiKey(self, key: str) -> None:
        """Persist the user's TMDB API key (empty string clears it)."""
        cleaned = (key or "").strip()
        db.set_setting("tmdb_api_key", cleaned)
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(bool, result=bool)
    def setLaunchAtLogin(self, enabled: bool) -> bool:
        """Toggle Windows launch-at-login. Returns the effective state."""
        effective = autostart.set_enabled(enabled)
        self.settingsChanged.emit(json.dumps(self._settings_dict()))
        return effective

    @pyqtSlot(result=str)
    def getSearchHistory(self) -> str:
        """Return the last 20 unique search queries, newest first."""
        raw = db.get_setting("search_history") or ""
        history = [entry for entry in raw.split("|") if entry]
        return json.dumps(history)

    @pyqtSlot(str)
    def rememberSearch(self, query: str) -> None:
        """Append a query to history, deduped, capped at 20 entries."""
        cleaned = (query or "").strip()
        if not cleaned:
            return
        raw = db.get_setting("search_history") or ""
        history = [entry for entry in raw.split("|") if entry and entry != cleaned]
        history.insert(0, cleaned)
        history = history[:20]
        db.set_setting("search_history", "|".join(history))

    @pyqtSlot()
    def clearSearchHistory(self) -> None:
        """Wipe the persisted search history."""
        db.set_setting("search_history", "")

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

        if self._metadata_worker is not None and self._metadata_worker.isRunning():
            self._metadata_worker.requestInterruption()
            self._metadata_worker.wait(1000)

        try:
            torrents.stop_session(self.session)
        except Exception as exc:
            logger.error(f"Session shutdown error: {exc}")
