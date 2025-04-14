"""Implementation of torrent control operations."""

import libtorrent as lt
from typing import Dict, Optional

from src.core.interfaces.torrent_session import ITorrentSession
from src.database.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger('torrent_controller')

class TorrentController:
    """Handles torrent control operations like pause and resume."""
    
    def __init__(self, session_manager: ITorrentSession, db_manager: DatabaseManager):
        """Initialize torrent controller.
        
        Args:
            session_manager: Manager for the libtorrent session
            db_manager: Manager for database operations
        """
        self.session_manager = session_manager
        self.db_manager = db_manager
        self.session = session_manager.session
        self.torrents = {}  # info_hash -> handle
        
        logger.info("TorrentController initialized")
    
    def pause_torrent(self, info_hash: str) -> bool:
        """Pause a torrent.
        
        Args:
            info_hash: The info hash of the torrent to pause
            
        Returns:
            True if the torrent was paused successfully, False otherwise
        """
        try:
            logger.info(f"Pausing torrent: {info_hash}")
            
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found: {info_hash}")
                return False
            
            handle.pause()
            self.db_manager.update_torrent_status(info_hash, "paused")
            
            logger.info(f"Torrent paused successfully: {info_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause torrent: {str(e)}")
            return False
    
    def resume_torrent(self, info_hash: str) -> bool:
        """Resume a paused torrent.
        
        Args:
            info_hash: The info hash of the torrent to resume
            
        Returns:
            True if the torrent was resumed successfully, False otherwise
        """
        try:
            logger.info(f"Resuming torrent: {info_hash}")
            
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found: {info_hash}")
                return False
            
            handle.resume()
            self.db_manager.update_torrent_status(info_hash, "downloading")
            
            logger.info(f"Torrent resumed successfully: {info_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume torrent: {str(e)}")
            return False
    
    def _get_handle(self, info_hash: str) -> Optional[lt.torrent_handle]:
        """Get the torrent handle for a given info hash.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            The torrent handle if found, None otherwise
        """
        try:
            return self.torrents.get(info_hash.lower())
        except Exception as e:
            logger.error(f"Failed to get torrent handle: {str(e)}")
            return None 