"""Search, provider discovery, and search-history slots."""

from __future__ import annotations

import json

from PyQt6.QtCore import pyqtSlot

import db
from providers import all_provider_choices, site_configs
from search.dto import SearchOptions
from utils.logger import setup_logger
from workers import ProviderHealthWorker, SearchWorker

logger = setup_logger("bridge.search")


class SearchMixin:
    """Mixin providing search and provider-discovery slots."""

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
        logger.info(
            f"Search started: query={query!r} page={page} mode={options.provider_mode.value}"
        )

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
