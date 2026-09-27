"""The Bridge class: signals, startup, shutdown and helpers the slot mixins share.

The slots live in the mixins. Signals are declared here so PyQt registers them once.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

import db
import torrents
from bridge.feeds_slots import FeedsMixin
from bridge.player_slots import PlayerMixin
from bridge.search_slots import SearchMixin
from bridge.settings_slots import SettingsMixin
from bridge.system_slots import SystemMixin
from bridge.torrents_slots import TorrentsMixin
from providers import all_provider_choices
from torrents.persistence import load_saved
from torrents.session import Session
from utils import autostart
from utils.logger import setup_logger
from workers import (
    DownloadsPollWorker,
    MetadataEnrichWorker,
    NetworkSpeedWorker,
    ProviderHealthWorker,
    RssPollWorker,
    ScheduledBandwidthWorker,
    SearchWorker,
    StreamPrepareWorker,
    WatchFolderWorker,
)

logger = setup_logger("bridge")


class Bridge(
    SystemMixin,
    SettingsMixin,
    FeedsMixin,
    SearchMixin,
    TorrentsMixin,
    PlayerMixin,
    QObject,
):
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
    clipboardMagnet = pyqtSignal(str)  # magnet URI found on the clipboard
    streamProgress = pyqtSignal(str)  # JSON: phase, message, buffer percentage

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
        self._completion_announced: set[str] = set()
        self._player_window = None
        self._stream_worker: Optional[StreamPrepareWorker] = None
        self._retired_workers: list[QThread] = []

        self.downloads_worker = DownloadsPollWorker(self.session)
        self.downloads_worker.snapshot.connect(self._on_downloads_snapshot)
        self.downloads_worker.start()

        self.network_worker = NetworkSpeedWorker(self.session)
        self.network_worker.speed.connect(self.networkSpeed)
        self.network_worker.start()

        watch_folder = db.get_setting("watch_folder") or ""
        self.watch_worker = WatchFolderWorker(self.session, watch_folder)
        self.watch_worker.added.connect(self._on_watch_added)
        if watch_folder:
            self.watch_worker.start()

        self.rss_worker = RssPollWorker(self.session)
        self.rss_worker.added.connect(
            lambda feed, h: self.toast.emit("info", f"RSS {feed}: added new item") if h else None
        )
        if (db.get_setting("rss_enabled") or "0") == "1":
            self.rss_worker.start()

        self.schedule_worker = ScheduledBandwidthWorker(self._apply_scheduled_limits)
        self.schedule_worker.start()

    def _retire_worker(self, worker: Optional[QThread]) -> None:
        """Keep a replaced worker referenced until its thread ends.

        If the old worker is simply overwritten while it runs, nothing can
        interrupt it and `shutdown` cannot wait for it before the libtorrent
        session stops. This polls `isRunning()` because several workers define
        their own `finished` signal, which hides Qt's.
        """
        alive: list[QThread] = []
        for retired in self._retired_workers:
            if retired.isRunning():
                alive.append(retired)
            else:
                # Returns at once for an ended thread, and makes sure it is
                # joined before the reference is dropped.
                retired.wait(50)
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            alive.append(worker)
        self._retired_workers = alive

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

    def _on_watch_added(self, path: str, info_hash: str) -> None:
        if info_hash:
            self.toast.emit("info", f"Auto-added from watch folder: {os.path.basename(path)}")

    def _apply_scheduled_limits(self, window: str) -> None:
        if window == "quiet":
            down = self._int_setting("schedule_quiet_down_kb_s", 0)
            up = self._int_setting("schedule_quiet_up_kb_s", 0)
            torrents.apply_limits(
                self.session,
                download_kb_s=down,
                upload_kb_s=up,
                active_downloads=self._int_setting("max_active_downloads", 0),
                active_seeds=self._int_setting("max_active_seeds", 0),
            )
        else:
            self._apply_session_limits_from_db()

    def _on_search_finished(
        self, query: str, page: int, results: list, total: int, pages: int
    ) -> None:
        self.searchCompleted.emit(
            json.dumps({
                "query": query,
                "page": page,
                "results": results,
                "total": total,
                "pages": pages,
            })
        )
        self._kick_metadata_enrich(query, results)

    def _kick_metadata_enrich(self, query: str, results: list) -> None:
        self._retire_worker(self._metadata_worker)
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

    def _enabled_provider_set(self) -> set[str]:
        raw = db.get_setting("enabled_providers")
        if raw is None:
            return {choice["key"] for choice in all_provider_choices() if choice["defaultOn"]}
        return {part.strip() for part in raw.split(",") if part.strip()}

    def _apply_enabled_providers(self, options: dict) -> dict:
        enabled = self._enabled_provider_set()
        stable_keys = {"piratebay_stable"}
        enabled_stable = sorted(enabled & stable_keys)
        enabled_vendor = sorted(
            key.split(":", 1)[1] for key in enabled if key.startswith("vendor:")
        )
        merged = dict(options)
        merged["enabledStable"] = enabled_stable
        if not merged.get("sites") and enabled_vendor:
            # For MULTI mode: no sites picked means the sites enabled in settings.
            merged.setdefault("sites", enabled_vendor)
        return merged

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
            "clipboardWatcher": _bool_setting("clipboard_watcher_enabled", "0"),
            "watchFolder": db.get_setting("watch_folder") or "",
            "dnsOverHttps": _bool_setting("dns_over_https_enabled"),
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

    def minimize_to_tray_enabled(self) -> bool:
        return (db.get_setting("minimize_to_tray") or "1") == "1"

    def shutdown(self) -> None:
        logger.info("Bridge shutting down")
        try:
            self.cancelStreamPrepare()
            self.closePlayer()
        except Exception as exc:
            logger.error(f"Player shutdown error: {exc}")
        for worker_name in (
            "downloads_worker",
            "network_worker",
            "watch_worker",
            "rss_worker",
            "schedule_worker",
        ):
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

        # Retired workers may still be running, and some of them use the
        # libtorrent session that is stopped below.
        for retired in self._retired_workers:
            try:
                retired.requestInterruption()
                retired.wait(1000)
            except Exception as exc:
                logger.error(f"Retired worker shutdown error: {exc}")
        self._retired_workers = []

        try:
            torrents.stop_session(self.session)
        except Exception as exc:
            logger.error(f"Session shutdown error: {exc}")
