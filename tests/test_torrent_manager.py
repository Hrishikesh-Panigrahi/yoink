import unittest
import libtorrent as lt
from unittest.mock import MagicMock, patch
from src.core.torrent_manager import TorrentManager
import os

class TestTorrentManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.torrent_manager = TorrentManager()
        self.test_magnet = "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678&dn=Test+Torrent"
        self.test_save_path = os.path.expanduser("~/Downloads")
        
        # Mock the database manager's add_torrent method
        self.torrent_manager.db_manager.add_torrent = MagicMock()
        self.torrent_manager.db_manager.remove_torrent = MagicMock()

    def test_add_torrent(self):
        """Test adding a torrent with a magnet link"""
        # Test successful torrent addition
        try:
            info_hash = self.torrent_manager.add_torrent(self.test_magnet)
            
            # Verify that the torrent was added
            self.assertIsNotNone(info_hash)
            self.assertTrue(isinstance(info_hash, str))
            
            # Verify that the torrent is in the manager's dictionary
            self.assertIn(info_hash, self.torrent_manager.torrents)
            
            # Get the torrent handle and verify its properties
            handle, info = self.torrent_manager.torrents[info_hash]
            self.assertTrue(isinstance(handle, lt.torrent_handle))
            
            # Verify save path
            status = handle.status()
            self.assertEqual(status.save_path, self.test_save_path)
            
            # Verify database manager was called
            self.torrent_manager.db_manager.add_torrent.assert_called_once()
            
        except Exception as e:
            self.fail(f"add_torrent raised an unexpected exception: {str(e)}")

    def test_add_torrent_invalid_magnet(self):
        """Test adding a torrent with an invalid magnet link"""
        invalid_magnet = "not-a-magnet-link"
        
        # Test that adding an invalid magnet link raises an exception
        with self.assertRaises(Exception):
            self.torrent_manager.add_torrent(invalid_magnet)
            
        # Verify database manager was not called
        self.torrent_manager.db_manager.add_torrent.assert_not_called()

    def test_add_torrent_with_custom_save_path(self):
        """Test adding a torrent with a custom save path"""
        custom_path = "/tmp/test_downloads"
        if not os.path.exists(custom_path):
            os.makedirs(custom_path)
            
        try:
            # Set custom save path
            self.torrent_manager.set_save_path(custom_path)
            
            # Add torrent
            info_hash = self.torrent_manager.add_torrent(self.test_magnet)
            
            # Verify that the torrent was added with the custom save path
            handle, info = self.torrent_manager.torrents[info_hash]
            status = handle.status()
            self.assertEqual(status.save_path, custom_path)
            
            # Verify database manager was called
            self.torrent_manager.db_manager.add_torrent.assert_called_once()
            
        finally:
            # Cleanup
            if os.path.exists(custom_path):
                os.rmdir(custom_path)

    def test_add_duplicate_torrent(self):
        """Test adding the same torrent twice"""
        # Add the torrent first time
        first_hash = self.torrent_manager.add_torrent(self.test_magnet)
        
        # Try to add the same torrent again
        second_hash = self.torrent_manager.add_torrent(self.test_magnet)
        
        # Verify that both operations return the same hash
        self.assertEqual(first_hash, second_hash)
        
        # Verify that only one instance exists in the torrents dictionary
        matching_torrents = [h for h in self.torrent_manager.torrents.keys() if h == first_hash]
        self.assertEqual(len(matching_torrents), 1)
        
        # Verify database manager was called only once
        self.assertEqual(self.torrent_manager.db_manager.add_torrent.call_count, 1)

    def tearDown(self):
        """Clean up after each test method."""
        # Remove all added torrents
        for hash in list(self.torrent_manager.torrents.keys()):
            self.torrent_manager.remove_torrent(hash, delete_files=True) 