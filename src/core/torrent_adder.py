"""Implementation of torrent adding operations."""

import os
import libtorrent as lt
from typing import Optional, Union
from pathlib import Path
from PyQt6.QtCore import QTimer

from src.core.interfaces.torrent_session import ITorrentSession
from src.database.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger('torrent_adder')

class TorrentAdder:
    """Handles adding torrents to the session."""
    
    def __init__(self, session_manager: ITorrentSession, db_manager: DatabaseManager):
        """Initialize torrent adder.
        
        Args:
            session_manager: Manager for the libtorrent session
            db_manager: Manager for database operations
        """
        self.session_manager = session_manager
        self.db_manager = db_manager
        self.session = session_manager.session
        self.torrents = {}  # info_hash -> handle
        self.save_path = self.db_manager.get_default_download_dir()
        
        logger.info(f"TorrentAdder initialized with save path: {self.save_path}")
    
    def add_torrent(self, magnet_link: str, save_path: Optional[str] = None) -> str:
        """Add a torrent via magnet link.
        
        Args:
            magnet_link: The magnet link of the torrent to add
            save_path: The directory to save the downloaded files
            
        Returns:
            The info hash of the added torrent
            
        Raises:
            ValueError: If the magnet link is invalid
        """
        try:
            logger.info(f"Adding torrent from magnet link: {magnet_link[:60]}...")
            
            # Validate magnet link
            if not magnet_link.startswith('magnet:'):
                raise ValueError("Invalid magnet link format")
            
            # Set up save path
            if not save_path:
                save_path = self.save_path
            
            # Create save directory if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)
                logger.info(f"Created save directory: {save_path}")
            
            # Add torrent to session
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = save_path
            handle = self.session.add_torrent(params)
            
            # Get info hash
            info_hash = str(handle.info_hash()).lower()
            
            # Store handle
            self.torrents[info_hash] = handle
            
            # Add to database if we have metadata
            if handle.has_metadata():
                self._add_to_database(handle, magnet_link, save_path)
            else:
                self._setup_metadata_handler(handle, magnet_link, save_path)
            
            logger.info(f"Torrent added successfully with hash: {info_hash}")
            return info_hash
            
        except Exception as e:
            logger.error(f"Failed to add torrent: {str(e)}")
            raise
    
    def add_torrent_file(self, torrent_file_path: Union[str, Path], save_path: Optional[str] = None) -> str:
        """Add a torrent via torrent file.
        
        Args:
            torrent_file_path: Path to the .torrent file
            save_path: The directory to save the downloaded files
            
        Returns:
            The info hash of the added torrent
            
        Raises:
            ValueError: If the torrent file is invalid
            FileNotFoundError: If the torrent file does not exist
        """
        try:
            logger.info(f"Adding torrent from file: {torrent_file_path}")
            
            # Validate file exists
            if not os.path.exists(torrent_file_path):
                raise FileNotFoundError(f"Torrent file not found: {torrent_file_path}")
            
            # Set up save path
            if not save_path:
                save_path = self.save_path
            
            # Create save directory if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)
                logger.info(f"Created save directory: {save_path}")
            
            # Add torrent to session
            info = lt.torrent_info(torrent_file_path)
            params = lt.add_torrent_params()
            params.ti = info
            params.save_path = save_path
            handle = self.session.add_torrent(params)
            
            # Get info hash
            info_hash = str(handle.info_hash()).lower()
            
            # Store handle
            self.torrents[info_hash] = handle
            
            # Add to database
            self._add_to_database(handle, str(torrent_file_path), save_path)
            
            logger.info(f"Torrent added successfully with hash: {info_hash}")
            return info_hash
            
        except Exception as e:
            logger.error(f"Failed to add torrent file: {str(e)}")
            raise
    
    def _setup_metadata_handler(self, handle: lt.torrent_handle, source: str, save_path: str) -> None:
        """Set up handler for metadata reception.
        
        Args:
            handle: The torrent handle
            source: The source of the torrent (magnet link or file path)
            save_path: The save path for the torrent
        """
        # Enable metadata receiving alerts
        self.session.apply_settings({'alert_mask': lt.alert.category_t.status_notification})
        
        # Set up metadata received alert handler
        def check_metadata():
            alerts = self.session.pop_alerts()
            for alert in alerts:
                if isinstance(alert, lt.metadata_received_alert):
                    if alert.handle.info_hash() == handle.info_hash():
                        self._add_to_database(alert.handle, source, save_path)
                        return True
            return False
        
        # Start a timer to check for metadata
        timer = QTimer()
        timer.timeout.connect(lambda: check_metadata() and timer.stop())
        timer.start(1000)  # Check every second
        
        logger.debug(f"Waiting for metadata for torrent: {handle.info_hash()}")
    
    def _add_to_database(self, handle: lt.torrent_handle, source: str, save_path: str) -> None:
        """Add torrent information to the database.
        
        Args:
            handle: The torrent handle
            source: The source of the torrent (magnet link or file path)
            save_path: The save path for the torrent
        """
        try:
            info = handle.get_torrent_info()
            name = info.name()
            size = info.total_size()
            files = info.files()
            
            # Add to database
            self.db_manager.add_torrent(
                name=name,
                magnet_link=source,
                info_hash=str(handle.info_hash()),
                size=size,
                save_path=save_path
            )
            
            logger.debug(f"Added torrent {name} to database")
            
        except Exception as e:
            logger.error(f"Failed to add torrent to database: {str(e)}")
            raise 