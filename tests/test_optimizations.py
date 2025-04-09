import unittest
import time
from src.core.torrent_manager import TorrentManager
from src.gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
import sys

class TestOptimizations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance
        cls.app = QApplication(sys.argv)
        
        # Initialize components
        cls.torrent_manager = TorrentManager()
        cls.main_window = MainWindow()

    def test_session_settings(self):
        """Test if session settings are properly optimized"""
        session = self.torrent_manager.session
        settings = session.get_settings()
        
        # Verify optimized settings
        self.assertEqual(settings['active_downloads'], -1)
        self.assertEqual(settings['active_seeds'], -1)
        self.assertEqual(settings['active_limit'], -1)
        self.assertEqual(settings['connections_limit'], 500)
        self.assertEqual(settings['tick_interval'], 100)
        self.assertEqual(settings['cache_size'], 1024 * 1024 * 1024)
        self.assertEqual(settings['disk_io_read_mode'], 2)
        self.assertEqual(settings['disk_io_write_mode'], 2)
        self.assertTrue(settings['enable_dht'])
        self.assertTrue(settings['enable_lsd'])
        self.assertTrue(settings['enable_upnp'])
        self.assertTrue(settings['enable_natpmp'])
        self.assertEqual(settings['upload_rate_limit'], 0)
        self.assertEqual(settings['download_rate_limit'], 0)
        
        # Verify DHT settings
        self.assertEqual(settings['dht_max_peers'], 500)
        self.assertEqual(settings['dht_max_fail_count'], 20)
        self.assertEqual(settings['dht_max_torrents'], 2000)
        self.assertEqual(settings['dht_max_dht_items'], 2000)
        self.assertEqual(settings['dht_search_branching'], 10)
        self.assertEqual(settings['dht_max_peers_reply'], 100)
        self.assertTrue(settings['dht_restrict_routing_ips'])
        self.assertEqual(settings['dht_max_torrent_search_reply'], 20)

    def test_connection_optimization(self):
        """Test if connection settings are properly optimized"""
        session = self.torrent_manager.session
        settings = session.get_settings()
        
        # Verify connection settings
        self.assertEqual(settings['connections_limit'], 500)
        self.assertEqual(settings['connection_speed'], 200)
        self.assertEqual(settings['peer_connect_timeout'], 2)
        self.assertEqual(settings['request_timeout'], 10)
        self.assertEqual(settings['peer_timeout'], 20)
        self.assertTrue(settings['enable_incoming_utp'])
        self.assertTrue(settings['enable_outgoing_utp'])
        self.assertTrue(settings['enable_incoming_tcp'])
        self.assertTrue(settings['enable_outgoing_tcp'])
        self.assertEqual(settings['max_peerlist_size'], 4000)
        self.assertEqual(settings['max_failcount'], 20)

    def test_ui_update_performance(self):
        """Test UI update performance"""
        start_time = time.time()
        
        # Simulate multiple UI updates without sleep
        for _ in range(10):
            self.main_window.batch_update_ui()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # UI updates should be fast (less than 100ms per update)
        self.assertLess(total_time / 10, 0.1)

    def test_network_speed_monitoring(self):
        """Test network speed monitoring performance"""
        start_time = time.time()
        
        # Simulate network speed checks without sleep
        for _ in range(5):
            self.main_window.check_network_speed()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Network speed checks should be fast (less than 50ms per check)
        self.assertLess(total_time / 5, 0.05)

    @classmethod
    def tearDownClass(cls):
        # Cleanup
        cls.torrent_manager.session = None  # Release session
        cls.main_window.close()
        cls.app.quit()

if __name__ == '__main__':
    unittest.main() 