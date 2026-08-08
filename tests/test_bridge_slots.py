"""Tests for the QWebChannel slots in `src/bridge/`.

`Bridge.__init__` opens a libtorrent session and starts five QThreads, none of
which a unit test wants. These tests build the object with `__new__` and run
`QObject.__init__` by hand, then attach a real (shared) torrent session and fake
workers. Signals still work — PyQt delivers direct connections without a running
QApplication — so every slot below is the real implementation.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from PyQt6.QtCore import QObject

import db
import feeds
import torrents
from bridge import Bridge, search_slots, settings_slots, system_slots

SIGNAL_NAMES = (
    "downloadsUpdated",
    "networkSpeed",
    "searchCompleted",
    "searchError",
    "saveFolderChanged",
    "toast",
    "settingsChanged",
    "requestNotification",
    "metadataEnriched",
    "providerHealth",
    "updateAvailable",
    "clipboardMagnet",
)


class Recorder:
    """Collects every signal the bridge emits, in order."""

    def __init__(self, bridge: Bridge) -> None:
        self.events: list[tuple] = []
        for name in SIGNAL_NAMES:
            getattr(bridge, name).connect(self._make_handler(name))

    def _make_handler(self, name: str):
        def handler(*args):
            self.events.append((name,) + args)

        return handler

    def named(self, name: str) -> list[tuple]:
        return [event for event in self.events if event[0] == name]

    def last(self, name: str) -> tuple:
        matches = self.named(name)
        assert matches, f"no {name} signal was emitted"
        return matches[-1]

    def clear(self) -> None:
        self.events.clear()


class FakeWorker:
    """Stands in for the QThread workers the slots poke at."""

    def __init__(self, running: bool = False) -> None:
        self.running = running
        self.starts = 0
        self.stops = 0
        self.waits = 0
        self.folder = ""
        self._last_window = "default"

    def isRunning(self) -> bool:
        return self.running

    def start(self) -> None:
        self.starts += 1
        self.running = True

    def stop(self) -> None:
        self.stops += 1
        self.running = False

    def wait(self, msecs: int = 0) -> bool:
        self.waits += 1
        return True

    def update_folder(self, folder: str) -> None:
        self.folder = folder


def stub_dialog(monkeypatch, module, **methods) -> None:
    """Replace a slot module's QFileDialog with one returning canned answers.

    The real `Option` enum is carried over: callers pass `QFileDialog.Option.
    ShowDirsOnly` straight through to the stub.
    """
    attrs = {name: staticmethod(fn) for name, fn in methods.items()}
    attrs["Option"] = module.QFileDialog.Option
    monkeypatch.setattr(module, "QFileDialog", type("StubDialog", (), attrs))


@pytest.fixture(scope="module")
def lt_session():
    """One real libtorrent session for the whole module — it is slow to build."""
    with tempfile.TemporaryDirectory(prefix="yoink-bridge-") as save_dir:
        session = torrents.create_session(save_dir)
        yield session
        torrents.stop_session(session)


@pytest.fixture
def bridge(lt_session, monkeypatch, tmp_path):
    """A Bridge with real slots, a real session, fake workers, and a fresh db."""
    db_file = tmp_path / "bridge-test.db"
    monkeypatch.setenv("TORRENT_DB_PATH", str(db_file))
    db.dispose_engine()
    db.init_db()

    obj = Bridge.__new__(Bridge)
    QObject.__init__(obj)
    obj.save_folder = str(tmp_path / "downloads")
    os.makedirs(obj.save_folder, exist_ok=True)
    obj.session = lt_session
    obj._search_worker = None
    obj._metadata_worker = None
    obj._health_worker = None
    obj._update_worker = None
    obj._completion_announced = set()
    obj.downloads_worker = FakeWorker(running=True)
    obj.network_worker = FakeWorker(running=True)
    obj.watch_worker = FakeWorker()
    obj.rss_worker = FakeWorker()
    obj.schedule_worker = FakeWorker()

    yield obj

    db.dispose_engine()


@pytest.fixture
def recorder(bridge):
    return Recorder(bridge)


# ----- Settings -----------------------------------------------------------


def test_get_settings_reports_defaults(bridge):
    settings = json.loads(bridge.getSettings())

    assert settings["saveFolder"] == bridge.save_folder
    assert settings["notifications"] is True
    assert settings["downloadLimitKbS"] == 0
    assert settings["seedRatioLimit"] == 0.0
    assert settings["tmdbConfigured"] is False
    assert settings["watchFolder"] == ""


def test_set_bool_setting_persists_and_notifies(bridge, recorder):
    bridge.setBoolSetting("notifications_enabled", False)

    assert db.get_setting("notifications_enabled") == "0"
    assert json.loads(recorder.last("settingsChanged")[1])["notifications"] is False


def test_set_int_setting_persists_and_reapplies_limits(bridge, recorder):
    bridge.setIntSetting("download_limit_kb_s", 512)

    assert db.get_setting("download_limit_kb_s") == "512"
    assert json.loads(recorder.last("settingsChanged")[1])["downloadLimitKbS"] == 512


def test_set_float_setting_rounds_to_four_places(bridge):
    bridge.setFloatSetting("seed_ratio_limit", 1.5)

    assert db.get_setting("seed_ratio_limit") == "1.5000"
    assert json.loads(bridge.getSettings())["seedRatioLimit"] == 1.5


def test_set_tmdb_api_key_trims_and_flags_configured(bridge):
    bridge.setTmdbApiKey("  secret-key  ")
    assert db.get_setting("tmdb_api_key") == "secret-key"
    assert json.loads(bridge.getSettings())["tmdbConfigured"] is True

    bridge.setTmdbApiKey("")
    assert json.loads(bridge.getSettings())["tmdbConfigured"] is False


def test_export_settings_omits_the_tmdb_key(bridge, recorder, monkeypatch, tmp_path):
    db.set_setting("tmdb_api_key", "secret-key")
    db.set_setting("download_limit_kb_s", "256")
    target = tmp_path / "exported.json"
    stub_dialog(
        monkeypatch,
        settings_slots,
        getSaveFileName=lambda *args, **kwargs: (str(target), "JSON Files (*.json)"),
    )

    written = bridge.exportSettings()

    assert written == str(target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["settings"]["download_limit_kb_s"] == "256"
    assert "tmdb_api_key" not in payload["settings"]
    assert recorder.last("toast")[1] == "success"


def test_export_settings_returns_empty_when_cancelled(bridge, monkeypatch):
    stub_dialog(
        monkeypatch,
        settings_slots,
        getSaveFileName=lambda *args, **kwargs: ("", ""),
    )

    assert bridge.exportSettings() == ""


def test_import_settings_applies_the_file(bridge, recorder, monkeypatch, tmp_path):
    source = tmp_path / "incoming.json"
    source.write_text(
        json.dumps({"settings": {"upload_limit_kb_s": "64", "minimize_to_tray": "0"}}),
        encoding="utf-8",
    )
    stub_dialog(
        monkeypatch,
        settings_slots,
        getOpenFileName=lambda *args, **kwargs: (str(source), ""),
    )

    assert bridge.importSettings() == str(source)
    settings = json.loads(recorder.last("settingsChanged")[1])
    assert settings["uploadLimitKbS"] == 64
    assert settings["minimizeToTray"] is False


def test_import_settings_rejects_a_file_without_a_settings_object(
    bridge, recorder, monkeypatch, tmp_path
):
    source = tmp_path / "bad.json"
    source.write_text(json.dumps({"settings": "nope"}), encoding="utf-8")
    stub_dialog(
        monkeypatch,
        settings_slots,
        getOpenFileName=lambda *args, **kwargs: (str(source), ""),
    )

    assert bridge.importSettings() == ""
    assert recorder.last("toast")[1] == "error"


def test_proxy_round_trips(bridge):
    bridge.setProxy("  http://127.0.0.1:8080  ", "  Yoink/1.0  ")

    proxy = json.loads(bridge.getProxy())
    assert proxy["proxyUrl"] == "http://127.0.0.1:8080"
    assert proxy["userAgent"] == "Yoink/1.0"


def test_schedule_round_trips_and_resets_the_worker_window(bridge):
    bridge.setSchedule(
        json.dumps(
            {
                "enabled": True,
                "quietStart": "23:00",
                "quietEnd": "07:00",
                "quietDownKbS": 100,
                "quietUpKbS": 50,
            }
        )
    )

    schedule = json.loads(bridge.getSchedule())
    assert schedule == {
        "enabled": True,
        "quietStart": "23:00",
        "quietEnd": "07:00",
        "quietDownKbS": 100,
        "quietUpKbS": 50,
    }
    # Cleared so the worker reapplies the caps on its next tick.
    assert bridge.schedule_worker._last_window == ""


def test_set_schedule_ignores_malformed_json(bridge):
    bridge.setSchedule("{not json")

    assert db.get_setting("schedule_enabled") is None
    assert bridge.schedule_worker._last_window == "default"


# ----- Search -------------------------------------------------------------


def test_search_with_a_blank_query_reports_an_error(bridge, recorder):
    bridge.search("   ", 1, "{}")

    assert recorder.last("searchError")[1] == "Please enter a search query."
    assert bridge._search_worker is None


def test_search_trims_the_query_and_clamps_the_page(bridge, monkeypatch):
    started = {}

    class FakeSearchWorker:
        def __init__(self, query, page, options):
            started.update(query=query, page=page, options=options)
            self.finished = _FakeSignal()
            self.failed = _FakeSignal()

        def start(self):
            started["started"] = True

        def isRunning(self):
            return False

    monkeypatch.setattr(search_slots, "SearchWorker", FakeSearchWorker)

    bridge.search("  ubuntu iso  ", 0, "{}")

    assert started["query"] == "ubuntu iso"
    assert started["page"] == 1
    assert started["started"] is True


def test_search_survives_malformed_options_json(bridge, monkeypatch):
    seen = {}

    class FakeSearchWorker:
        def __init__(self, query, page, options):
            seen["options"] = options
            self.finished = _FakeSignal()
            self.failed = _FakeSignal()

        def start(self):
            pass

        def isRunning(self):
            return False

    monkeypatch.setattr(search_slots, "SearchWorker", FakeSearchWorker)

    bridge.search("ubuntu", 1, "[[[not an object")

    assert seen["options"] is not None


class _FakeSignal:
    def connect(self, _slot) -> None:
        pass


def test_provider_toggle_is_persisted_and_reflected(bridge, recorder):
    bridge.setProviderEnabled("yts", False)

    choices = {c["key"]: c for c in json.loads(bridge.getProviderChoices())}
    assert choices["yts"]["enabled"] is False
    assert recorder.named("settingsChanged")

    bridge.setProviderEnabled("yts", True)
    choices = {c["key"]: c for c in json.loads(bridge.getProviderChoices())}
    assert choices["yts"]["enabled"] is True


def test_apply_enabled_providers_splits_stable_from_vendor(bridge):
    db.set_setting("enabled_providers", "yts,vendor:1337x,vendor:nyaa")

    merged = bridge._apply_enabled_providers({})

    assert merged["enabledStable"] == ["yts"]
    assert merged["sites"] == ["1337x", "nyaa"]


def test_apply_enabled_providers_keeps_an_explicit_site_list(bridge):
    db.set_setting("enabled_providers", "yts,vendor:1337x")

    merged = bridge._apply_enabled_providers({"sites": ["nyaa"]})

    assert merged["sites"] == ["nyaa"]


def test_search_history_dedupes_newest_first_and_caps_at_twenty(bridge):
    bridge.rememberSearch("alpha")
    bridge.rememberSearch("beta")
    bridge.rememberSearch("alpha")

    assert json.loads(bridge.getSearchHistory()) == ["alpha", "beta"]

    for index in range(30):
        bridge.rememberSearch(f"query-{index}")

    history = json.loads(bridge.getSearchHistory())
    assert len(history) == 20
    assert history[0] == "query-29"


def test_search_history_ignores_blank_queries_and_can_be_cleared(bridge):
    bridge.rememberSearch("alpha")
    bridge.rememberSearch("   ")

    assert json.loads(bridge.getSearchHistory()) == ["alpha"]

    bridge.clearSearchHistory()
    assert json.loads(bridge.getSearchHistory()) == []


# ----- Torrents -----------------------------------------------------------


def test_add_torrent_rejects_an_empty_magnet(bridge, recorder):
    result = json.loads(bridge.addTorrent("   "))

    assert result == {"hash": "", "wasExisting": False}
    assert recorder.last("toast")[1] == "error"


def test_add_torrent_from_bytes_rejects_an_empty_payload(bridge, recorder):
    result = json.loads(bridge.addTorrentFromBytes("x.torrent", "!!!"))

    assert result == {"hash": "", "wasExisting": False}
    assert recorder.last("toast")[2] == "Empty .torrent payload"


def test_torrent_queries_degrade_to_empty_for_unknown_hashes(bridge):
    assert bridge.getTorrentFiles("deadbeef") == "[]"
    assert bridge.getDownloadFile("deadbeef") == ""
    assert bridge.getDownloadFile("") == ""
    assert bridge.pauseTorrent("deadbeef") is False
    assert bridge.resumeTorrent("deadbeef") is False


def test_set_file_priorities_rejects_a_non_object_payload(bridge):
    assert bridge.setFilePriorities("deadbeef", "[1, 2, 3]") is False


def test_labels_are_normalized_deduped_and_sorted(bridge):
    bridge.setLabels("ABCDEF", json.dumps(["  hd ", "hd", "anime", ""]))

    assert json.loads(bridge.getLabels("abcdef")) == ["anime", "hd"]
    # Lookup is case-insensitive on the hash.
    assert json.loads(bridge.getLabels("ABCDEF")) == ["anime", "hd"]


def test_set_labels_ignores_a_non_list_payload(bridge):
    bridge.setLabels("abcdef", json.dumps({"not": "a list"}))

    assert json.loads(bridge.getLabels("abcdef")) == []


def test_get_all_labels_returns_the_union(bridge):
    bridge.setLabels("aaa", json.dumps(["hd", "anime"]))
    bridge.setLabels("bbb", json.dumps(["hd", "docs"]))

    assert json.loads(bridge.getAllLabels()) == ["anime", "docs", "hd"]


# ----- Downloads snapshot -------------------------------------------------


def test_snapshot_announces_each_completion_once(bridge, recorder):
    payload = [{"hash": "abc", "name": "Movie", "progress": 100, "status": "Seeding"}]

    bridge._on_downloads_snapshot(payload)
    bridge._on_downloads_snapshot(payload)

    assert json.loads(recorder.last("downloadsUpdated")[1]) == payload
    assert len(recorder.named("requestNotification")) == 1
    assert recorder.last("requestNotification")[1:] == ("Download complete", "Movie")


def test_snapshot_stays_quiet_for_unfinished_torrents(bridge, recorder):
    bridge._on_downloads_snapshot(
        [
            {"hash": "abc", "name": "Movie", "progress": 42, "status": "Downloading"},
            {"hash": "def", "name": "Show", "progress": 100, "status": "Checking"},
        ]
    )

    assert recorder.named("requestNotification") == []


def test_snapshot_respects_the_notifications_toggle(bridge, recorder):
    db.set_setting("notifications_enabled", "0")

    bridge._on_downloads_snapshot(
        [{"hash": "abc", "name": "Movie", "progress": 100, "status": "Finished"}]
    )

    assert recorder.named("downloadsUpdated")
    assert recorder.named("requestNotification") == []


# ----- Feeds --------------------------------------------------------------


def test_add_feed_starts_the_poller_and_enables_rss(bridge, recorder):
    feed_id = bridge.addFeed("https://example.com/rss", "Example", "1080p", 5)

    stored = json.loads(bridge.getFeeds())
    assert [f["id"] for f in stored] == [feed_id]
    assert stored[0]["name"] == "Example"
    assert stored[0]["filterRegex"] == "1080p"
    assert stored[0]["minSeeders"] == 5
    assert db.get_setting("rss_enabled") == "1"
    assert bridge.rss_worker.starts == 1
    assert recorder.last("toast")[1] == "success"


def test_add_feed_leaves_a_running_poller_alone(bridge):
    bridge.rss_worker.running = True

    bridge.addFeed("https://example.com/rss", "", "", 0)

    assert bridge.rss_worker.starts == 0


def test_remove_feed_only_reports_a_real_removal(bridge, recorder):
    feed_id = bridge.addFeed("https://example.com/rss", "Example", "", 0)
    recorder.clear()

    bridge.removeFeed(feed_id)
    assert recorder.last("toast")[1] == "success"
    assert json.loads(bridge.getFeeds()) == []

    recorder.clear()
    bridge.removeFeed(feed_id)
    assert recorder.named("toast") == []


def test_get_feeds_survives_a_corrupt_settings_row(bridge, monkeypatch):
    def boom():
        raise RuntimeError("db exploded")

    monkeypatch.setattr(feeds, "load_feeds", boom)

    assert bridge.getFeeds() == "[]"


# ----- System -------------------------------------------------------------


def test_pick_watch_folder_persists_and_starts_the_worker(bridge, recorder, monkeypatch, tmp_path):
    target = tmp_path / "watched"
    target.mkdir()
    stub_dialog(
        monkeypatch,
        system_slots,
        getExistingDirectory=lambda *args, **kwargs: str(target),
    )

    assert bridge.pickWatchFolder() == str(target)
    assert db.get_setting("watch_folder") == str(target)
    assert bridge.watch_worker.folder == str(target)
    assert bridge.watch_worker.starts == 1
    assert json.loads(recorder.last("settingsChanged")[1])["watchFolder"] == str(target)


def test_pick_watch_folder_keeps_the_old_value_when_cancelled(bridge, monkeypatch):
    db.set_setting("watch_folder", "C:/existing")
    stub_dialog(monkeypatch, system_slots, getExistingDirectory=lambda *args, **kwargs: "")

    assert bridge.pickWatchFolder() == "C:/existing"
    assert bridge.watch_worker.starts == 0


def test_clear_watch_folder_stops_watching(bridge, recorder):
    db.set_setting("watch_folder", "C:/existing")

    bridge.clearWatchFolder()

    assert db.get_setting("watch_folder") == ""
    assert bridge.watch_worker.folder == ""
    assert json.loads(recorder.last("settingsChanged")[1])["watchFolder"] == ""


def test_pick_save_folder_updates_the_session_and_db(bridge, recorder, monkeypatch, tmp_path):
    target = tmp_path / "new-downloads"
    target.mkdir()
    stub_dialog(
        monkeypatch,
        system_slots,
        getExistingDirectory=lambda *args, **kwargs: str(target),
    )

    assert bridge.pickSaveFolder() == str(target)
    assert bridge.save_folder == str(target)
    assert db.get_setting("download_directory") == str(target)
    assert recorder.last("saveFolderChanged")[1] == str(target)


def test_about_info_reports_the_running_version(bridge):
    from version import __app_homepage__, __version__

    about = json.loads(bridge.getAboutInfo())

    assert about["version"] == __version__
    assert about["homepage"] == __app_homepage__
    assert about["python"]


def test_notify_respects_the_notifications_toggle(bridge, recorder):
    bridge.notify("info", "Title", "Body")
    assert recorder.last("requestNotification")[1:] == ("Title", "Body")

    db.set_setting("notifications_enabled", "0")
    recorder.clear()
    bridge.notify("info", "Title", "Body")
    assert recorder.named("requestNotification") == []


def test_every_listed_command_has_a_handler(bridge, monkeypatch):
    dispatched = []
    for command in json.loads(bridge.listCommands()):
        # `openSaveFolder` is dispatched with an argument; the rest take none.
        monkeypatch.setattr(
            bridge,
            command["id"],
            lambda *args, cid=command["id"]: dispatched.append(cid),
            raising=False,
        )

    for command in json.loads(bridge.listCommands()):
        bridge.runCommand(command["id"])

    assert dispatched == [c["id"] for c in json.loads(bridge.listCommands())]


def test_run_command_ignores_an_unknown_id(bridge, recorder):
    bridge.runCommand("does-not-exist")

    assert recorder.events == []


def test_open_path_ignores_a_blank_target(bridge, recorder, monkeypatch):
    monkeypatch.setattr(
        system_slots.os, "startfile", lambda *a: pytest.fail("should not open"), raising=False
    )

    bridge.openPath("   ")

    assert recorder.events == []


# ----- Shutdown -----------------------------------------------------------


def test_shutdown_stops_every_worker_and_the_session(bridge, monkeypatch):
    stopped = []
    monkeypatch.setattr(torrents, "stop_session", lambda session: stopped.append(session))

    bridge.shutdown()

    for name in ("downloads_worker", "network_worker", "watch_worker", "rss_worker",
                 "schedule_worker"):
        worker = getattr(bridge, name)
        assert worker.stops == 1, f"{name} was not stopped"
        assert worker.waits == 1, f"{name} was not waited on"
    assert stopped == [bridge.session]


def test_shutdown_continues_past_a_failing_worker(bridge, monkeypatch):
    monkeypatch.setattr(torrents, "stop_session", lambda session: None)

    def explode():
        raise RuntimeError("worker wedged")

    bridge.downloads_worker.stop = explode

    bridge.shutdown()

    assert bridge.network_worker.stops == 1
