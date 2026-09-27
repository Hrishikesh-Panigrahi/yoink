from __future__ import annotations

import json

from PyQt6.QtCore import pyqtSlot

import db
import feeds
from utils.logger import setup_logger

logger = setup_logger("bridge.feeds")


class FeedsMixin:
    @pyqtSlot(result=str)
    def getFeeds(self) -> str:
        try:
            payload = [
                {
                    "id": f.id,
                    "url": f.url,
                    "name": f.name,
                    "filterRegex": f.filter_regex,
                    "minSeeders": f.min_seeders,
                    "enabled": f.enabled,
                }
                for f in feeds.load_feeds()
            ]
            return json.dumps(payload)
        except Exception as exc:
            logger.error(f"getFeeds failed: {exc}")
            return "[]"

    @pyqtSlot(str, str, str, int, result=str)
    def addFeed(self, url: str, name: str, filter_regex: str, min_seeders: int) -> str:
        cfg = feeds.add_feed(url, name, filter_regex, int(min_seeders or 0))
        if not self.rss_worker.isRunning():
            db.set_setting("rss_enabled", "1")
            self.rss_worker.start()
        self.toast.emit("success", f"Subscribed to {cfg.name or cfg.url}")
        return cfg.id

    @pyqtSlot(str)
    def removeFeed(self, feed_id: str) -> None:
        if feeds.remove_feed(feed_id):
            self.toast.emit("success", "Feed removed")
