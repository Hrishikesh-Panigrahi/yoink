"""Tests for libtorrent session tuning and bridge snapshot performance."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest

from PyQt6.QtWidgets import QApplication

import db
import torrents
from bridge import Bridge


class TestSessionOptimizations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._old_db_path = os.environ.get("TORRENT_DB_PATH")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.close()
        cls._db_file = tmp.name
        os.environ["TORRENT_DB_PATH"] = cls._db_file
        db.dispose_engine()
        db.init_db()

        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.session = torrents.create_session(os.path.expanduser("~/Downloads"))
        cls.bridge = Bridge()

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.bridge.shutdown()
        except Exception:
            pass
        try:
            torrents.stop_session(cls.session)
        except Exception:
            pass
        db.dispose_engine()
        cls.app.quit()

        if cls._old_db_path is None:
            os.environ.pop("TORRENT_DB_PATH", None)
        else:
            os.environ["TORRENT_DB_PATH"] = cls._old_db_path
        if os.path.exists(cls._db_file):
            os.remove(cls._db_file)

    def test_session_settings_are_optimized(self) -> None:
        settings = self.session.lt_session.get_settings()

        self.assertEqual(settings["active_downloads"], -1)
        self.assertEqual(settings["active_seeds"], -1)
        self.assertEqual(settings["active_limit"], -1)
        self.assertEqual(settings["connections_limit"], 500)
        self.assertEqual(settings["tick_interval"], 100)
        self.assertEqual(settings["cache_size"], 1024 * 1024 * 1024)
        self.assertEqual(settings["disk_io_read_mode"], 2)
        self.assertEqual(settings["disk_io_write_mode"], 2)
        self.assertTrue(settings["enable_dht"])
        self.assertTrue(settings["enable_lsd"])
        self.assertTrue(settings["enable_upnp"])
        self.assertTrue(settings["enable_natpmp"])

        self.assertEqual(settings["dht_max_peers"], 500)
        self.assertEqual(settings["dht_max_torrents"], 2000)
        self.assertTrue(settings["dht_restrict_routing_ips"])

    def test_connection_settings_are_tuned(self) -> None:
        settings = self.session.lt_session.get_settings()
        self.assertEqual(settings["connection_speed"], 200)
        self.assertEqual(settings["peer_connect_timeout"], 2)
        self.assertEqual(settings["request_timeout"], 10)
        self.assertEqual(settings["peer_timeout"], 20)
        self.assertTrue(settings["enable_incoming_utp"])
        self.assertTrue(settings["enable_outgoing_utp"])
        self.assertEqual(settings["max_peerlist_size"], 4000)

    def test_bridge_get_downloads_is_fast(self) -> None:
        start = time.time()
        for _ in range(10):
            self.bridge.getDownloads()
        average = (time.time() - start) / 10
        self.assertLess(average, 0.1)

    def test_network_status_query_is_fast(self) -> None:
        start = time.time()
        for _ in range(5):
            status = self.bridge.session.lt_session.status()
            _ = (status.download_rate, status.upload_rate)
        average = (time.time() - start) / 5
        self.assertLess(average, 0.05)


if __name__ == "__main__":
    unittest.main()
