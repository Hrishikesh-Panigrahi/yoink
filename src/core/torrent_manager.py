"""Torrent Manager implementation that orchestrates torrent operations."""

import logging
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import libtorrent as lt

from src.core.interfaces.torrent_session import ITorrentSession
from src.core.interfaces.torrent_operations import ITorrentOperations
from src.core.interfaces.torrent_info_service import ITorrentInfoService, TorrentInfo
from src.core.torrent_session import TorrentSession
from src.core.torrent_operations import TorrentOperations
from src.core.torrent_info_service import TorrentInfoService
from src.database.database import DatabaseManager
from src.utils.logger import setup_logger

# Set up logger
logger = setup_logger('torrent_manager')

class TorrentManager:
    """Torrent Manager that orchestrates all torrent operations.
    
    This class follows the Facade pattern, providing a simplified interface
    to the complex subsystem of torrent operations, session management,
    and information retrieval.
    """
    
    def __init__(self):
        """Initialize TorrentManager with default settings."""
        logger.info("Initializing TorrentManager")
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Initialize session
        self.session_manager = TorrentSession()
        self.session = self.session_manager.session
        
        # Start the session
        self.session_manager.start_session()
        
        # Initialize torrent operations
        self.torrent_operations = TorrentOperations(self.session_manager, self.db_manager)
        
        # Initialize info service
        self.info_service = TorrentInfoService(self.session)
        
        # Get default download directory from database
        self.save_path = self.db_manager.get_setting('default_download_dir')
        if not self.save_path:
            self.save_path = os.path.expanduser("~/Downloads")
            self.db_manager.set_setting('default_download_dir', self.save_path)
        
        logger.info(f"TorrentManager initialized with save path: {self.save_path}")
        
        # Load saved torrents
        self._load_saved_torrents()
        
        # Optimize session
        self._optimize_session()
    
    def __del__(self):
        """Cleanup when the manager is destroyed."""
        try:
            logger.info("Cleaning up TorrentManager")
            self.session_manager.stop_session()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _load_saved_torrents(self):
        """Load previously saved torrents from the database."""
        try:
            logger.info("Loading saved torrents from database")
            torrents = self.db_manager.get_all_torrents()
            
            for torrent in torrents:
                try:
                    logger.debug(f"Loading torrent: {torrent.name}")
                    
                    # Add torrent back to session
                    params = lt.parse_magnet_uri(torrent.magnet_link)
                    params.save_path = torrent.save_path
                    
                    # Check if save path exists
                    if not os.path.exists(torrent.save_path):
                        os.makedirs(torrent.save_path)
                        logger.info(f"Created save directory: {torrent.save_path}")
                    
                    # Add to session
                    self.session.add_torrent(params)
                    
                except Exception as e:
                    logger.error(f"Error loading torrent {torrent.name}: {e}")
            
            logger.info(f"Loaded {len(torrents)} torrents from database")
            
        except Exception as e:
            logger.error(f"Error loading saved torrents: {e}")
    
    def _optimize_session(self):
        """Apply optimized settings to the session."""
        # Optimize connections
        self.session_manager.optimize_connections()
        
        # Setup bandwidth management with defaults
        download_limit = self.db_manager.get_setting('download_limit_kbps')
        upload_limit = self.db_manager.get_setting('upload_limit_kbps')
        
        if download_limit:
            self.session_manager.set_download_limit(int(download_limit))
        
        if upload_limit:
            self.session_manager.set_upload_limit(int(upload_limit))
    
    # === Facade methods for torrent operations ===
    
    def add_torrent(self, magnet_link: str) -> str:
        """Add a torrent via magnet link.
        
        Args:
            magnet_link: The magnet link of the torrent to add
            
        Returns:
            The info hash of the added torrent
            
        Raises:
            ValueError: If the magnet link is invalid
        """
        return self.torrent_operations.add_torrent(magnet_link, self.save_path)
    
    def add_torrent_file(self, torrent_file_path: str) -> str:
        """Add a torrent via torrent file.
        
        Args:
            torrent_file_path: Path to the .torrent file
            
        Returns:
            The info hash of the added torrent
            
        Raises:
            ValueError: If the torrent file is invalid
            FileNotFoundError: If the torrent file does not exist
        """
        return self.torrent_operations.add_torrent_file(torrent_file_path, self.save_path)
    
    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent.
        
        Args:
            info_hash: The info hash of the torrent to remove
            delete_files: Whether to delete the downloaded files
            
        Returns:
            True if the torrent was removed successfully, False otherwise
        """
        return self.torrent_operations.remove_torrent(info_hash, delete_files)
    
    def pause_torrent(self, info_hash: str) -> bool:
        """Pause a torrent.
        
        Args:
            info_hash: The info hash of the torrent to pause
            
        Returns:
            True if the torrent was paused successfully, False otherwise
        """
        return self.torrent_operations.pause_torrent(info_hash)
    
    def resume_torrent(self, info_hash: str) -> bool:
        """Resume a paused torrent.
        
        Args:
            info_hash: The info hash of the torrent to resume
            
        Returns:
            True if the torrent was resumed successfully, False otherwise
        """
        return self.torrent_operations.resume_torrent(info_hash)
    
    def set_file_priorities(self, info_hash: str, file_priorities: Dict[int, int]) -> bool:
        """Set the priorities of individual files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            file_priorities: Dictionary mapping file indices to priority values
            
        Returns:
            True if the priorities were set successfully, False otherwise
        """
        return self.torrent_operations.set_file_priorities(info_hash, file_priorities)
    
    # === Facade methods for torrent info ===
    
    def get_torrent_info(self, info_hash: str) -> Optional[TorrentInfo]:
        """Get information about a specific torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            TorrentInfo object if the torrent exists, None otherwise
        """
        return self.info_service.get_torrent_info(info_hash)
    
    def get_all_torrents(self) -> List[Tuple[str, TorrentInfo]]:
        """Get information about all torrents.
        
        Returns:
            List of tuples containing info hash and TorrentInfo
        """
        return self.info_service.get_all_torrents()
    
    def get_torrent_files(self, info_hash: str) -> List[Dict[str, Any]]:
        """Get information about files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            List of dictionaries containing file information
        """
        return self.info_service.get_torrent_files(info_hash)
    
    def get_torrent_peers(self, info_hash: str) -> List[Dict[str, Any]]:
        """Get information about peers for a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            List of dictionaries containing peer information
        """
        return self.info_service.get_torrent_peers(info_hash)
    
    # === Configuration methods ===
    
    def set_save_path(self, path: str):
        """Set the default save path for torrents.
        
        Args:
            path: The directory to save downloaded files
        """
        logger.info(f"Setting save path to: {path}")
        self.save_path = path
        self.db_manager.set_setting('default_download_dir', path)
    
    def set_download_limit(self, limit_kbps: int):
        """Set download bandwidth limit.
        
        Args:
            limit_kbps: Download limit in kilobytes per second
        """
        self.session_manager.set_download_limit(limit_kbps)
        self.db_manager.set_setting('download_limit_kbps', str(limit_kbps))
    
    def set_upload_limit(self, limit_kbps: int):
        """Set upload bandwidth limit.
        
        Args:
            limit_kbps: Upload limit in kilobytes per second
        """
        self.session_manager.set_upload_limit(limit_kbps)
        self.db_manager.set_setting('upload_limit_kbps', str(limit_kbps))
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics.
        
        Returns:
            Dictionary of session statistics
        """
        return self.session_manager.get_session_stats() 