"""QThread workers that drive the bridge's async signals."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

import torrents
from providers import health, tmdb
from search import search as run_search
from search.dto import SearchOptions
from torrents.session import Session
from utils.logger import setup_logger

logger = setup_logger("workers")


class SearchWorker(QThread):
    """Run a torrent search off the UI thread."""

    finished = pyqtSignal(str, int, list, int, int)  # query, page, results-as-dicts, total, pages
    failed = pyqtSignal(str, str)  # query, error message

    def __init__(self, query: str, page: int, options: Optional[SearchOptions] = None):
        super().__init__()
        self.query = query
        self.page = page
        self.options = options or SearchOptions()

    def run(self) -> None:
        try:
            page = run_search(self.query, self.page, options=self.options)
            payload = [r.to_dict() for r in page.results]
            self.finished.emit(self.query, self.page, payload, page.total, page.pages)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Search failed")
            self.failed.emit(self.query, str(exc))


class MetadataEnrichWorker(QThread):
    """Fan out TMDB lookups in parallel for the visible result page."""

    enriched = pyqtSignal(str, list)  # query, list of {key, metadata}

    def __init__(self, query: str, results: list, max_workers: int = 6):
        super().__init__()
        self.query = query
        self.results = results
        self.max_workers = max_workers

    def run(self) -> None:
        if not tmdb.get_api_key() or not self.results:
            return
        try:
            updates: List[dict] = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(self._lookup, item): item for item in self.results
                }
                for future in futures:
                    if self.isInterruptionRequested():
                        break
                    try:
                        result = future.result()
                    except Exception as exc:
                        logger.warning(f"TMDB enrich worker entry failed: {exc}")
                        continue
                    if result:
                        updates.append(result)
            if updates:
                self.enriched.emit(self.query, updates)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(f"Metadata enrich worker failed: {exc}")

    @staticmethod
    def _lookup(item: dict) -> Optional[dict]:
        title = item.get("title") or ""
        year = tmdb.extract_year(title, item.get("date"))
        meta = tmdb.enrich(title, year)
        if not meta:
            return None
        key = item.get("magnet") or item.get("infoHash") or title
        return {"key": key, "metadata": meta}


class ProviderHealthWorker(QThread):
    """Run provider health probes off the UI thread."""

    finished = pyqtSignal(dict)

    def run(self) -> None:
        try:
            statuses = health.ping_all()
            self.finished.emit(statuses)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(f"Health worker failed: {exc}")
            self.finished.emit({})


class UpdateCheckWorker(QThread):
    """Check GitHub Releases for a newer build."""

    finished = pyqtSignal(object)  # update dict or None

    def run(self) -> None:
        try:
            from utils.updater import check_for_update

            self.finished.emit(check_for_update())
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(f"Update check worker failed: {exc}")
            self.finished.emit(None)


class DownloadsPollWorker(QThread):
    """Poll the torrent session once per interval and push snapshots."""

    snapshot = pyqtSignal(list)

    def __init__(self, session: Session, interval_ms: int = 1000):
        super().__init__()
        self.session = session
        self.interval_ms = interval_ms
        self._running = True

    def run(self) -> None:
        while self._running:
            delay = self.interval_ms
            try:
                payload = [s.to_dict() for s in torrents.list_torrents(self.session)]
                self.snapshot.emit(payload)
                if not payload:
                    delay = max(self.interval_ms, 3000)
            except Exception as exc:
                logger.error(f"Downloads poll error: {exc}")
            self.msleep(delay)

    def stop(self) -> None:
        self._running = False


class WatchFolderWorker(QThread):
    """Poll a folder for new .torrent files and add them to the session (7.1)."""

    added = pyqtSignal(str, str)  # path, info hash

    def __init__(self, session: Session, folder: str, interval_ms: int = 10000):
        super().__init__()
        self.session = session
        self.folder = folder
        self.interval_ms = interval_ms
        self._running = True

    def update_folder(self, folder: str) -> None:
        self.folder = folder or ""

    def run(self) -> None:
        from torrents import watch

        while self._running:
            try:
                if self.folder:
                    for path in watch.discover(self.folder):
                        try:
                            info_hash = torrents.add_torrent_file(self.session, path)
                            watch.mark_processed(path)
                            self.added.emit(path, info_hash)
                        except Exception as exc:
                            logger.warning(f"Watch-folder add failed for {path}: {exc}")
            except Exception as exc:
                logger.error(f"Watch-folder poll error: {exc}")
            self.msleep(self.interval_ms)

    def stop(self) -> None:
        self._running = False


class RssPollWorker(QThread):
    """Poll subscribed RSS feeds and auto-add matching items (7.2)."""

    added = pyqtSignal(str, str)  # feed name, info hash

    def __init__(self, session: Session, interval_ms: int = 600_000):
        super().__init__()
        self.session = session
        self.interval_ms = interval_ms
        self._running = True

    def run(self) -> None:
        import re

        import feeds

        while self._running:
            try:
                for feed in feeds.load_feeds():
                    if not feed.enabled:
                        continue
                    pattern = re.compile(feed.filter_regex, re.I) if feed.filter_regex else None
                    seen = feeds.get_seen(feed.id)
                    new_guids = []
                    for item in feeds.fetch_feed_items(feed.url):
                        if item["guid"] in seen:
                            continue
                        if pattern and not pattern.search(item["title"]):
                            new_guids.append(item["guid"])
                            continue
                        if feed.min_seeders and item.get("seeders", 0) < feed.min_seeders:
                            new_guids.append(item["guid"])
                            continue
                        try:
                            info_hash = torrents.add_magnet(self.session, item["magnet"])
                            self.added.emit(feed.name or feed.url, info_hash)
                        except Exception as exc:
                            logger.warning(f"RSS add failed: {exc}")
                        new_guids.append(item["guid"])
                    if new_guids:
                        feeds.mark_seen(feed.id, new_guids)
            except Exception as exc:
                logger.error(f"RSS poll error: {exc}")
            self.msleep(self.interval_ms)

    def stop(self) -> None:
        self._running = False


class ScheduledBandwidthWorker(QThread):
    """Apply different bandwidth caps at user-defined time ranges (5.2)."""

    applied = pyqtSignal(str)  # window name

    def __init__(self, apply_callback, interval_ms: int = 60_000):
        super().__init__()
        self.apply_callback = apply_callback
        self.interval_ms = interval_ms
        self._running = True
        self._last_window = ""

    def run(self) -> None:
        import db

        while self._running:
            try:
                if (db.get_setting("schedule_enabled") or "0") == "1":
                    window = self._current_window()
                    if window != self._last_window:
                        self._last_window = window
                        self.apply_callback(window)
                        self.applied.emit(window)
            except Exception as exc:
                logger.error(f"Schedule worker error: {exc}")
            self.msleep(self.interval_ms)

    def stop(self) -> None:
        self._running = False

    @staticmethod
    def _current_window() -> str:
        import time

        import db

        try:
            start = (db.get_setting("schedule_quiet_start") or "00:00").strip()
            end = (db.get_setting("schedule_quiet_end") or "08:00").strip()
            now = time.localtime()
            minutes = now.tm_hour * 60 + now.tm_min
            start_m = ScheduledBandwidthWorker._parse_minutes(start)
            end_m = ScheduledBandwidthWorker._parse_minutes(end)
            if start_m == end_m:
                return "default"
            if start_m < end_m:
                in_window = start_m <= minutes < end_m
            else:
                in_window = minutes >= start_m or minutes < end_m
            return "quiet" if in_window else "default"
        except Exception:
            return "default"

    @staticmethod
    def _parse_minutes(hhmm: str) -> int:
        try:
            h, m = hhmm.split(":", 1)
            return int(h) * 60 + int(m)
        except Exception:
            return 0


class NetworkSpeedWorker(QThread):
    """Poll the libtorrent session for aggregate throughput."""

    speed = pyqtSignal(float, float)  # download KB/s, upload KB/s

    def __init__(self, session: Session, interval_ms: int = 1000):
        super().__init__()
        self.session = session
        self.interval_ms = interval_ms
        self._running = True

    def run(self) -> None:
        while self._running:
            delay = self.interval_ms
            try:
                stats = torrents.network_stats(self.session)
                self.speed.emit(stats.download_kb_s, stats.upload_kb_s)
                if stats.download_kb_s <= 0 and stats.upload_kb_s <= 0:
                    delay = max(self.interval_ms, 3000)
            except Exception as exc:
                logger.error(f"Network speed poll error: {exc}")
            self.msleep(delay)

    def stop(self) -> None:
        self._running = False
