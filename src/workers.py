"""QThread workers that drive the bridge's async signals."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

import torrents
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
            try:
                payload = [s.to_dict() for s in torrents.list_torrents(self.session)]
                self.snapshot.emit(payload)
            except Exception as exc:
                logger.error(f"Downloads poll error: {exc}")
            self.msleep(self.interval_ms)

    def stop(self) -> None:
        self._running = False


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
            try:
                stats = torrents.network_stats(self.session)
                self.speed.emit(stats.download_kb_s, stats.upload_kb_s)
            except Exception as exc:
                logger.error(f"Network speed poll error: {exc}")
            self.msleep(self.interval_ms)

    def stop(self) -> None:
        self._running = False
