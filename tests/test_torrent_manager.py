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


if __name__ == "__main__":
    unittest.main()
