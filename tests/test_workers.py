"""Tests for the QThread workers in `src/workers.py`.

Tests call `run()` directly instead of `start()`, so the work stays on the test
thread and signals arrive synchronously without an event loop. The polling
workers loop until `stop()`, so their tests call `stop()` from a signal handler
or a patched `msleep` to end after one pass.
"""

from __future__ import annotations

import json

import pytest

import feeds
import torrents
import workers
from providers import health, tmdb
from search.dto import SearchOptions
from torrents.dto import NetworkStats


class FakeResult:
    def __init__(self, title: str) -> None:
        self.title = title

    def to_dict(self) -> dict:
        return {"title": self.title}


class FakePage:
    def __init__(self, results, total=0, pages=1) -> None:
        self.results = results
        self.total = total
        self.pages = pages


def collect(signal) -> list:
    """Return a list that records every emission of `signal`."""
    received: list = []
    signal.connect(lambda *args: received.append(args if len(args) != 1 else args[0]))
    return received


# SearchWorker


def test_search_worker_emits_result_dicts(monkeypatch):
    captured = {}

    def fake_search(query, page, options=None):
        captured.update(query=query, page=page, options=options)
        return FakePage([FakeResult("Ubuntu 24.04")], total=1, pages=3)

    monkeypatch.setattr(workers, "run_search", fake_search)
    worker = workers.SearchWorker("ubuntu", 2, SearchOptions())
    received = collect(worker.finished)

    worker.run()

    assert received == [("ubuntu", 2, [{"title": "Ubuntu 24.04"}], 1, 3)]
    assert captured["page"] == 2


def test_search_worker_defaults_its_options():
    worker = workers.SearchWorker("ubuntu", 1)

    assert isinstance(worker.options, SearchOptions)


def test_search_worker_reports_failures_without_raising(monkeypatch):
    def explode(query, page, options=None):
        raise RuntimeError("provider down")

    monkeypatch.setattr(workers, "run_search", explode)
    worker = workers.SearchWorker("ubuntu", 1, SearchOptions())
    failures = collect(worker.failed)
    finishes = collect(worker.finished)

    worker.run()

    assert failures == [("ubuntu", "provider down")]
    assert finishes == []


def interrupt(worker, monkeypatch) -> None:
    """Make a worker look interrupted.

    `requestInterruption` does nothing on a thread that was never started, and
    these tests call `run()` on the test thread, so the check is stubbed.
    """
    monkeypatch.setattr(worker, "isInterruptionRequested", lambda: True)


def test_search_worker_drops_results_once_superseded(monkeypatch):
    monkeypatch.setattr(
        workers, "run_search", lambda q, p, options=None: FakePage([FakeResult("Ubuntu")])
    )
    worker = workers.SearchWorker("ubuntu", 1, SearchOptions())
    finishes = collect(worker.finished)
    interrupt(worker, monkeypatch)

    worker.run()

    assert finishes == []


def test_search_worker_stays_quiet_about_a_superseded_failure(monkeypatch):
    def explode(query, page, options=None):
        raise RuntimeError("provider down")

    monkeypatch.setattr(workers, "run_search", explode)
    worker = workers.SearchWorker("ubuntu", 1, SearchOptions())
    failures = collect(worker.failed)
    interrupt(worker, monkeypatch)

    worker.run()

    assert failures == []


# MetadataEnrichWorker


def test_metadata_worker_does_nothing_without_an_api_key(monkeypatch):
    monkeypatch.setattr(tmdb, "get_api_key", lambda: "")
    worker = workers.MetadataEnrichWorker("ubuntu", [{"title": "Movie (2019)"}])
    received = collect(worker.enriched)

    worker.run()

    assert received == []


def test_metadata_worker_does_nothing_without_results(monkeypatch):
    monkeypatch.setattr(tmdb, "get_api_key", lambda: "key")
    worker = workers.MetadataEnrichWorker("ubuntu", [])
    received = collect(worker.enriched)

    worker.run()

    assert received == []


def test_metadata_worker_emits_one_entry_per_hit(monkeypatch):
    monkeypatch.setattr(tmdb, "get_api_key", lambda: "key")
    monkeypatch.setattr(tmdb, "extract_year", lambda title, date: 2019)
    monkeypatch.setattr(
        tmdb,
        "enrich",
        lambda title, year: {"poster": "p.jpg"} if "Known" in title else None,
    )
    worker = workers.MetadataEnrichWorker(
        "movies",
        [
            {"title": "Known Movie", "magnet": "magnet:?xt=1"},
            {"title": "Unknown Movie", "magnet": "magnet:?xt=2"},
        ],
        max_workers=2,
    )
    received = collect(worker.enriched)

    worker.run()

    assert len(received) == 1
    query, updates = received[0]
    assert query == "movies"
    assert updates == [{"key": "magnet:?xt=1", "metadata": {"poster": "p.jpg"}}]


def test_metadata_worker_skips_entries_that_raise(monkeypatch):
    monkeypatch.setattr(tmdb, "get_api_key", lambda: "key")
    monkeypatch.setattr(tmdb, "extract_year", lambda title, date: None)

    def flaky(title, year):
        if title == "Bad":
            raise RuntimeError("tmdb 500")
        return {"poster": "p.jpg"}

    monkeypatch.setattr(tmdb, "enrich", flaky)
    worker = workers.MetadataEnrichWorker(
        "movies", [{"title": "Bad"}, {"title": "Good"}], max_workers=2
    )
    received = collect(worker.enriched)

    worker.run()

    assert received[0][1] == [{"key": "Good", "metadata": {"poster": "p.jpg"}}]


@pytest.mark.parametrize(
    "item, expected_key",
    [
        ({"title": "T", "magnet": "magnet:?xt=1", "infoHash": "abc"}, "magnet:?xt=1"),
        ({"title": "T", "infoHash": "abc"}, "abc"),
        ({"title": "T"}, "T"),
    ],
)
def test_metadata_lookup_key_prefers_magnet_then_hash_then_title(
    monkeypatch, item, expected_key
):
    monkeypatch.setattr(tmdb, "extract_year", lambda title, date: None)
    monkeypatch.setattr(tmdb, "enrich", lambda title, year: {"poster": "p.jpg"})

    assert workers.MetadataEnrichWorker._lookup(item)["key"] == expected_key


def test_metadata_lookup_returns_none_when_tmdb_has_nothing(monkeypatch):
    monkeypatch.setattr(tmdb, "extract_year", lambda title, date: None)
    monkeypatch.setattr(tmdb, "enrich", lambda title, year: None)

    assert workers.MetadataEnrichWorker._lookup({"title": "T"}) is None


# ProviderHealthWorker


def test_health_worker_forwards_the_status_map(monkeypatch):
    monkeypatch.setattr(health, "ping_all", lambda: {"piratebay_stable": {"ok": True}})
    worker = workers.ProviderHealthWorker()
    received = collect(worker.finished)

    worker.run()

    assert received == [{"piratebay_stable": {"ok": True}}]


def test_health_worker_emits_an_empty_map_on_failure(monkeypatch):
    def explode():
        raise RuntimeError("network down")

    monkeypatch.setattr(health, "ping_all", explode)
    worker = workers.ProviderHealthWorker()
    received = collect(worker.finished)

    worker.run()

    assert received == [{}]


# DownloadsPollWorker


class FakeSnapshot:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


def test_downloads_worker_emits_a_snapshot_then_stops(monkeypatch):
    monkeypatch.setattr(
        torrents, "list_torrents", lambda session: [FakeSnapshot({"hash": "abc"})]
    )
    worker = workers.DownloadsPollWorker(session=object(), interval_ms=1)
    received: list = []
    worker.snapshot.connect(lambda payload: (received.append(payload), worker.stop()))

    worker.run()

    assert received == [[{"hash": "abc"}]]


def test_downloads_worker_keeps_polling_after_an_error(monkeypatch):
    calls = {"n": 0}

    def flaky(session):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("session busy")
        return [FakeSnapshot({"hash": "abc"})]

    monkeypatch.setattr(torrents, "list_torrents", flaky)
    worker = workers.DownloadsPollWorker(session=object(), interval_ms=1)
    worker.snapshot.connect(lambda payload: worker.stop())

    worker.run()

    assert calls["n"] == 2


# NetworkSpeedWorker


def test_network_worker_emits_throughput_then_stops(monkeypatch):
    monkeypatch.setattr(
        torrents, "network_stats", lambda session: NetworkStats(12.5, 3.25)
    )
    worker = workers.NetworkSpeedWorker(session=object(), interval_ms=1)
    received: list = []
    worker.speed.connect(lambda down, up: (received.append((down, up)), worker.stop()))

    worker.run()

    assert received == [(12.5, 3.25)]


# WatchFolderWorker


def test_watch_worker_adds_discovered_files_and_marks_them(monkeypatch):
    from torrents import watch

    marked: list = []
    monkeypatch.setattr(watch, "discover", lambda folder: ["C:/watched/a.torrent"])
    monkeypatch.setattr(watch, "mark_processed", marked.append)
    monkeypatch.setattr(torrents, "add_torrent_file", lambda session, path: "hash-a")
    worker = workers.WatchFolderWorker(session=object(), folder="C:/watched", interval_ms=1)
    received: list = []
    worker.added.connect(lambda path, h: (received.append((path, h)), worker.stop()))

    worker.run()

    assert received == [("C:/watched/a.torrent", "hash-a")]
    assert marked == ["C:/watched/a.torrent"]


def test_watch_worker_leaves_a_failed_add_unmarked(monkeypatch):
    from torrents import watch

    marked: list = []
    attempts = {"n": 0}

    def discover(folder):
        attempts["n"] += 1
        if attempts["n"] > 1:
            worker.stop()
        return ["C:/watched/bad.torrent"]

    def explode(session, path):
        raise RuntimeError("corrupt torrent")

    monkeypatch.setattr(watch, "discover", discover)
    monkeypatch.setattr(watch, "mark_processed", marked.append)
    monkeypatch.setattr(torrents, "add_torrent_file", explode)
    worker = workers.WatchFolderWorker(session=object(), folder="C:/watched", interval_ms=1)

    worker.run()

    assert marked == []


def test_watch_worker_skips_the_scan_when_no_folder_is_set(monkeypatch):
    from torrents import watch

    def discover(folder):
        pytest.fail("discover should not run without a folder")

    monkeypatch.setattr(watch, "discover", discover)
    worker = workers.WatchFolderWorker(session=object(), folder="", interval_ms=1)
    worker._running = True

    # Stop after the first pass.
    original_msleep = worker.msleep
    worker.msleep = lambda ms: (worker.stop(), original_msleep(0))
    worker.run()

    worker.update_folder("C:/watched")
    assert worker.folder == "C:/watched"
    worker.update_folder("")
    assert worker.folder == ""


# RssPollWorker


def _feed(**overrides):
    return feeds.FeedConfig(
        id=overrides.get("id", "feed-1"),
        url=overrides.get("url", "https://example.com/rss"),
        name=overrides.get("name", "Example"),
        filter_regex=overrides.get("filter_regex", ""),
        min_seeders=overrides.get("min_seeders", 0),
        enabled=overrides.get("enabled", True),
    )


def _rss_item(title: str, guid: str, seeders: int = 100) -> dict:
    return {"title": title, "magnet": f"magnet:?xt={guid}", "guid": guid, "seeders": seeders}


def _run_rss_once(monkeypatch, feed, items, seen=()):
    """Run one RSS poll pass and return (added signals, guids marked seen)."""
    marked: list = []
    added: list = []
    monkeypatch.setattr(feeds, "load_feeds", lambda: [feed])
    monkeypatch.setattr(feeds, "fetch_feed_items", lambda url: items)
    monkeypatch.setattr(feeds, "get_seen", lambda feed_id: set(seen))
    monkeypatch.setattr(feeds, "mark_seen", lambda feed_id, guids: marked.extend(guids))
    monkeypatch.setattr(torrents, "add_magnet", lambda session, magnet: f"hash-{magnet[-1]}")

    worker = workers.RssPollWorker(session=object(), interval_ms=1)
    worker.added.connect(lambda name, h: added.append((name, h)))
    original_msleep = worker.msleep
    worker.msleep = lambda ms: (worker.stop(), original_msleep(0))

    worker.run()
    return added, marked


def test_rss_worker_adds_every_item_when_unfiltered(monkeypatch):
    added, marked = _run_rss_once(
        monkeypatch, _feed(), [_rss_item("Show S01E01 1080p", "1"), _rss_item("Show S01E02", "2")]
    )

    assert added == [("Example", "hash-1"), ("Example", "hash-2")]
    assert marked == ["1", "2"]


def test_rss_worker_honours_the_filter_regex(monkeypatch):
    added, marked = _run_rss_once(
        monkeypatch,
        _feed(filter_regex="1080p"),
        [_rss_item("Show S01E01 1080p", "1"), _rss_item("Show S01E02 720p", "2")],
    )

    assert added == [("Example", "hash-1")]
    # Filtered-out items are marked seen too, so they are not checked again.
    assert sorted(marked) == ["1", "2"]


def test_rss_worker_honours_the_seeder_floor(monkeypatch):
    added, marked = _run_rss_once(
        monkeypatch,
        _feed(min_seeders=10),
        [_rss_item("Popular", "1", seeders=50), _rss_item("Dead", "2", seeders=2)],
    )

    assert added == [("Example", "hash-1")]
    assert sorted(marked) == ["1", "2"]


def test_rss_worker_ignores_already_seen_guids(monkeypatch):
    added, marked = _run_rss_once(
        monkeypatch, _feed(), [_rss_item("Show S01E01", "1")], seen=("1",)
    )

    assert added == []
    assert marked == []


def test_rss_worker_skips_disabled_feeds(monkeypatch):
    added, marked = _run_rss_once(
        monkeypatch, _feed(enabled=False), [_rss_item("Show S01E01", "1")]
    )

    assert added == []
    assert marked == []


def test_rss_worker_falls_back_to_the_url_when_a_feed_is_unnamed(monkeypatch):
    added, _ = _run_rss_once(monkeypatch, _feed(name=""), [_rss_item("Show", "1")])

    assert added == [("https://example.com/rss", "hash-1")]


# ScheduledBandwidthWorker


@pytest.mark.parametrize(
    "text, expected",
    [
        ("00:00", 0),
        ("08:30", 510),
        ("23:59", 1439),
        ("garbage", 0),
        ("", 0),
        ("12", 0),
    ],
)
def test_parse_minutes(text, expected):
    assert workers.ScheduledBandwidthWorker._parse_minutes(text) == expected


@pytest.mark.parametrize(
    "start, end, now_minutes, expected",
    [
        # Same-day window.
        ("09:00", "17:00", 10 * 60, "quiet"),
        ("09:00", "17:00", 8 * 60, "default"),
        ("09:00", "17:00", 17 * 60, "default"),  # end is exclusive
        ("09:00", "17:00", 9 * 60, "quiet"),  # start is inclusive
        # Window wrapping past midnight.
        ("23:00", "07:00", 23 * 60 + 30, "quiet"),
        ("23:00", "07:00", 3 * 60, "quiet"),
        ("23:00", "07:00", 12 * 60, "default"),
        # A zero-width window is off.
        ("08:00", "08:00", 8 * 60, "default"),
    ],
)
def test_current_window(monkeypatch, start, end, now_minutes, expected):
    import time as time_module

    import db

    monkeypatch.setattr(
        db,
        "get_setting",
        lambda key: {"schedule_quiet_start": start, "schedule_quiet_end": end}.get(key),
    )
    monkeypatch.setattr(
        time_module,
        "localtime",
        lambda *args: time_module.struct_time(
            (2026, 1, 1, now_minutes // 60, now_minutes % 60, 0, 0, 1, 0)
        ),
    )

    assert workers.ScheduledBandwidthWorker._current_window() == expected


def test_current_window_defaults_when_settings_are_unreadable(monkeypatch):
    import db

    def explode(key):
        raise RuntimeError("db gone")

    monkeypatch.setattr(db, "get_setting", explode)

    assert workers.ScheduledBandwidthWorker._current_window() == "default"


def test_schedule_worker_only_fires_on_a_window_change(monkeypatch):
    import db

    applied: list = []
    windows = iter(["quiet", "quiet", "default"])
    monkeypatch.setattr(db, "get_setting", lambda key: "1")
    monkeypatch.setattr(
        workers.ScheduledBandwidthWorker, "_current_window", staticmethod(lambda: next(windows))
    )

    worker = workers.ScheduledBandwidthWorker(applied.append, interval_ms=1)
    ticks = {"n": 0}
    original_msleep = worker.msleep

    def counted_msleep(ms):
        ticks["n"] += 1
        if ticks["n"] >= 3:
            worker.stop()
        original_msleep(0)

    worker.msleep = counted_msleep
    worker.run()

    assert applied == ["quiet", "default"]


def test_schedule_worker_stays_idle_while_disabled(monkeypatch):
    import db

    applied: list = []
    monkeypatch.setattr(db, "get_setting", lambda key: "0")

    worker = workers.ScheduledBandwidthWorker(applied.append, interval_ms=1)
    original_msleep = worker.msleep
    worker.msleep = lambda ms: (worker.stop(), original_msleep(0))
    worker.run()

    assert applied == []


# StreamPrepareWorker
#
# Used when playing a search result. It waits for metadata, starts the stream,
# then waits for the head of the file to reach disk before playback opens it.


class MetadataHandle(FakeSnapshot):
    """A handle whose metadata arrives after a set number of polls."""

    def __init__(self, ready_after=0, valid=True):
        self.polls = 0
        self.ready_after = ready_after
        self._valid = valid

    def is_valid(self):
        return self._valid

    def has_metadata(self):
        self.polls += 1
        return self.polls > self.ready_after


def stream_worker(monkeypatch, handles, **kwargs):
    session = type("S", (), {"handles": handles, "streams": {}})()
    return workers.StreamPrepareWorker(session, "abc", poll_ms=1, **kwargs)


def test_stream_prepare_reports_a_missing_torrent(monkeypatch):
    worker = stream_worker(monkeypatch, {})
    failures = collect(worker.failed)

    worker.run()

    assert "no longer in the session" in failures[0][1]


def test_stream_prepare_gives_up_waiting_for_metadata(monkeypatch):
    worker = stream_worker(
        monkeypatch, {"abc": MetadataHandle(ready_after=10_000)}, metadata_timeout_s=0.05
    )
    failures = collect(worker.failed)
    phases = collect(worker.progress)

    worker.run()

    assert "file list" in failures[0][1]
    assert json.loads(phases[0])["phase"] == "metadata"


def test_stream_prepare_reports_a_torrent_with_no_video(monkeypatch):
    monkeypatch.setattr(torrents, "start_stream", lambda *a, **k: None)
    worker = stream_worker(monkeypatch, {"abc": MetadataHandle()})
    failures = collect(worker.failed)

    worker.run()

    assert "Nothing playable" in failures[0][1]


def _status(head_have, head_total, path):
    from torrents.dto import StreamStatus

    return StreamStatus(
        info_hash="abc", file_index=2, path="Movie.mkv", absolute_path=path,
        size=100, first_piece=0, last_piece=9, head_have=head_have,
        head_total=head_total, tail_have=0, tail_total=2, sequential=True,
    )


def test_stream_prepare_waits_for_the_head_then_reports_ready(monkeypatch, tmp_path):
    target = tmp_path / "Movie.mkv"
    target.write_bytes(b"x")
    monkeypatch.setattr(torrents, "start_stream", lambda *a, **k: _status(0, 4, str(target)))
    states = iter([_status(1, 4, str(target)), _status(2, 4, str(target)),
                   _status(4, 4, str(target))])
    monkeypatch.setattr(torrents, "stream_status", lambda *a: next(states))

    worker = stream_worker(monkeypatch, {"abc": MetadataHandle()})
    ready = collect(worker.ready)
    updates = collect(worker.progress)

    worker.run()

    assert ready == [("abc", 2)]
    assert any(json.loads(u)["phase"] == "buffering" for u in updates)


def test_stream_prepare_will_not_open_a_file_that_is_not_on_disk_yet(monkeypatch, tmp_path):
    # libtorrent creates the file on its first write. Before that, VLC would be
    # handed a path that does not exist.
    missing = str(tmp_path / "not-written-yet.mkv")
    monkeypatch.setattr(torrents, "start_stream", lambda *a, **k: _status(4, 4, missing))
    monkeypatch.setattr(torrents, "stream_status", lambda *a: _status(4, 4, missing))

    worker = stream_worker(monkeypatch, {"abc": MetadataHandle()}, buffer_timeout_s=0.05)
    ready = collect(worker.ready)
    failures = collect(worker.failed)

    worker.run()

    assert ready == []
    assert "Gave up waiting" in failures[0][1]


def test_stream_prepare_stops_when_asked(monkeypatch, tmp_path):
    target = tmp_path / "Movie.mkv"
    target.write_bytes(b"x")
    monkeypatch.setattr(torrents, "start_stream", lambda *a, **k: _status(0, 4, str(target)))
    worker = stream_worker(monkeypatch, {"abc": MetadataHandle()})
    monkeypatch.setattr(
        torrents, "stream_status", lambda *a: (worker.stop(), _status(0, 4, str(target)))[1]
    )
    ready = collect(worker.ready)
    failures = collect(worker.failed)

    worker.run()

    assert ready == [] and failures == []


# StreamPrepareWorker: dead-swarm reporting


class SwarmHandle(MetadataHandle):
    """A handle reporting a fixed swarm state."""

    def __init__(self, peers=0, seeds=0, rate=0.0):
        super().__init__()
        self._peers, self._seeds, self._rate = peers, seeds, rate

    def status(self):
        return type(
            "S", (), {"num_peers": self._peers, "num_seeds": self._seeds,
                      "download_rate": self._rate}
        )()


@pytest.mark.parametrize(
    "percent, peers, seeds, rate, expected",
    [
        (0.0, 0, 0, 0.0, "Looking for peers..."),
        (0.0, 2, 1, 0.0, "Buffering 0% - connected to 2, waiting for data"),
        (40.0, 3, 2, 250.0, "Buffering 40% at 250 KB/s"),
    ],
)
def test_buffer_message_explains_the_hold_up(percent, peers, seeds, rate, expected):
    assert workers.StreamPrepareWorker._buffer_message(percent, peers, seeds, rate) == expected


def test_stream_prepare_gives_up_when_no_data_arrives(monkeypatch, tmp_path):
    target = tmp_path / "Movie.mkv"
    target.write_bytes(b"x")
    stuck = _status(0, 8, str(target))          # head never fills
    monkeypatch.setattr(torrents, "start_stream", lambda *a, **k: stuck)
    monkeypatch.setattr(torrents, "stream_status", lambda *a: stuck)

    worker = stream_worker(
        monkeypatch, {"abc": SwarmHandle(peers=1, seeds=1)},
        no_data_timeout_s=0.05, buffer_timeout_s=30,
    )
    failures = collect(worker.failed)
    ready = collect(worker.ready)

    worker.run()

    assert ready == []
    assert "No data arriving" in failures[0][1]
    assert "1 seed(s), 1 peer(s)" in failures[0][1]


def test_stream_prepare_keeps_waiting_while_the_head_is_filling(monkeypatch, tmp_path):
    # Each bit of progress resets the no-data timeout.
    target = tmp_path / "Movie.mkv"
    target.write_bytes(b"x")
    states = iter([_status(n, 4, str(target)) for n in (0, 1, 2, 3, 4)])
    monkeypatch.setattr(torrents, "start_stream", lambda *a, **k: _status(0, 4, str(target)))
    monkeypatch.setattr(torrents, "stream_status", lambda *a: next(states))

    worker = stream_worker(
        monkeypatch, {"abc": SwarmHandle(peers=2, seeds=1, rate=120.0)},
        no_data_timeout_s=5.0,
    )
    ready = collect(worker.ready)
    failures = collect(worker.failed)

    worker.run()

    assert ready == [("abc", 2)]
    assert failures == []


def test_swarm_reads_zeroes_for_a_missing_handle(monkeypatch):
    worker = stream_worker(monkeypatch, {})

    assert worker._swarm() == (0, 0, 0.0)


# FreeProxyWorker


def test_free_proxy_worker_reports_progress_and_the_result(monkeypatch):
    def fake_find(on_progress, should_stop):
        on_progress(10, 400, 1)
        return {"proxy": "http://203.0.113.7:8080"}

    monkeypatch.setattr(workers.free_proxies, "find", fake_find)
    worker = workers.FreeProxyWorker()
    progress = collect(worker.progress)
    finished = collect(worker.finished)

    worker.run()

    assert progress == [(10, 400, 1)]
    assert finished == [{"proxy": "http://203.0.113.7:8080"}]
