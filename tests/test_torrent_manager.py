"""Tests for the torrents package (session + actions)."""

from __future__ import annotations

import os
import tempfile
import unittest

import libtorrent as lt

import db
import torrents


def _normalize(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(os.path.expanduser(path))))


TEST_MAGNET = (
    "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678&dn=Test+Torrent"
)


class TestTorrentActions(unittest.TestCase):
    def setUp(self) -> None:
        self._old_db_path = os.environ.get("TORRENT_DB_PATH")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.close()
        self._db_file = tmp.name
        os.environ["TORRENT_DB_PATH"] = self._db_file
        db.dispose_engine()
        db.init_db()

        self.save_path = os.path.expanduser("~/Downloads")
        self.session = torrents.create_session(self.save_path)

    def tearDown(self) -> None:
        for info_hash in list(self.session.handles.keys()):
            try:
                torrents.remove(self.session, info_hash, delete_files=False)
            except Exception:
                pass
        torrents.stop_session(self.session)
        db.dispose_engine()

        if self._old_db_path is None:
            os.environ.pop("TORRENT_DB_PATH", None)
        else:
            os.environ["TORRENT_DB_PATH"] = self._old_db_path

        if os.path.exists(self._db_file):
            os.remove(self._db_file)

    def test_add_magnet_returns_info_hash(self) -> None:
        info_hash = torrents.add_magnet(self.session, TEST_MAGNET)
        self.assertIsInstance(info_hash, str)
        self.assertIn(info_hash, self.session.handles)

        handle = self.session.handles[info_hash]
        self.assertIsInstance(handle, lt.torrent_handle)
        self.assertEqual(_normalize(handle.status().save_path), _normalize(self.save_path))

    def test_add_magnet_rejects_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            torrents.add_magnet(self.session, "not-a-magnet")

    def test_add_magnet_with_custom_save_path(self) -> None:
        custom = tempfile.mkdtemp(prefix="yoink-test-")
        try:
            torrents.set_save_path(self.session, custom)
            info_hash = torrents.add_magnet(self.session, TEST_MAGNET)
            handle = self.session.handles[info_hash]
            self.assertEqual(_normalize(handle.status().save_path), _normalize(custom))
        finally:
            try:
                os.rmdir(custom)
            except OSError:
                pass

    def test_adding_same_magnet_twice_is_idempotent(self) -> None:
        first = torrents.add_magnet(self.session, TEST_MAGNET)
        second = torrents.add_magnet(self.session, TEST_MAGNET)
        self.assertEqual(first, second)
        matching = [h for h in self.session.handles if h == first]
        self.assertEqual(len(matching), 1)

    def test_pause_all_and_resume_all_touch_every_handle(self) -> None:
        torrents.add_magnet(self.session, TEST_MAGNET)
        paused = torrents.pause_all(self.session)
        self.assertEqual(paused, 1)
        resumed = torrents.resume_all(self.session)
        self.assertEqual(resumed, 1)

    def test_set_file_priorities_returns_false_without_metadata(self) -> None:
        info_hash = torrents.add_magnet(self.session, TEST_MAGNET)
        # Magnet-only torrents have no metadata yet, so prioritize must no-op.
        ok = torrents.set_file_priorities(self.session, info_hash, {0: 0})
        self.assertFalse(ok)

    def test_list_files_returns_empty_when_metadata_missing(self) -> None:
        info_hash = torrents.add_magnet(self.session, TEST_MAGNET)
        self.assertEqual(torrents.list_files(self.session, info_hash), [])

    def test_apply_limits_does_not_raise(self) -> None:
        torrents.apply_limits(
            self.session,
            download_kb_s=512,
            upload_kb_s=128,
            active_downloads=3,
            active_seeds=5,
        )
        # Unsetting (passing 0) should also work
        torrents.apply_limits(self.session, download_kb_s=0, upload_kb_s=0)


class TestAutostart(unittest.TestCase):
    def test_is_enabled_returns_bool(self) -> None:
        from utils import autostart

        result = autostart.is_enabled()
        self.assertIsInstance(result, bool)

    def test_set_enabled_noop_off_windows(self) -> None:
        import sys

        from utils import autostart

        if sys.platform == "win32":
            self.skipTest("Skipped on Windows where it would touch the registry")
        # Should be a no-op everywhere else and report False.
        self.assertFalse(autostart.set_enabled(True))


if __name__ == "__main__":
    unittest.main()
