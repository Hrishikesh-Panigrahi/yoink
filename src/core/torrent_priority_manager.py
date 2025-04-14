"""Implementation of torrent priority management operations."""

import libtorrent as lt
from typing import Dict, Optional

from src.core.interfaces.torrent_session import ITorrentSession
from src.database.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger('torrent_priority_manager')

class TorrentPriorityManager:
    """Handles torrent priority management operations."""
    
    def __init__(self, session_manager: ITorrentSession, db_manager: DatabaseManager):
        """Initialize torrent priority manager.
        
        Args:
            session_manager: Manager for the libtorrent session
            db_manager: Manager for database operations
        """
        self.session_manager = session_manager
        self.db_manager = db_manager
        self.session = session_manager.session
        self.torrents = {}  # info_hash -> handle
        
        logger.info("TorrentPriorityManager initialized")
    
    def set_torrent_priority(self, info_hash: str, priority: int) -> bool:
        """Set the priority of a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            priority: The priority value (0-7, where 7 is highest)
            
        Returns:
            True if the priority was set successfully, False otherwise
        """
        try:
            logger.info(f"Setting priority {priority} for torrent: {info_hash}")
            
            # Validate priority
            if not 0 <= priority <= 7:
                logger.error(f"Invalid priority value: {priority}")
                return False
            
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found: {info_hash}")
                return False
            
            handle.set_priority(priority)
            self.db_manager.update_torrent_priority(info_hash, priority)
            
            logger.info(f"Priority set successfully for torrent: {info_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set torrent priority: {str(e)}")
            return False
    
    def set_file_priorities(self, info_hash: str, file_priorities: Dict[int, int]) -> bool:
        """Set the priorities of individual files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            file_priorities: Dictionary mapping file indices to priority values
            
        Returns:
            True if the priorities were set successfully, False otherwise
        """
        try:
            logger.info(f"Setting file priorities for torrent: {info_hash}")
            
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found: {info_hash}")
                return False
            
            # Validate priorities
            for file_idx, priority in file_priorities.items():
                if not 0 <= priority <= 7:
                    logger.error(f"Invalid priority value for file {file_idx}: {priority}")
                    return False
            
            # Set file priorities
            for file_idx, priority in file_priorities.items():
                handle.file_priority(file_idx, priority)
            
            # Update database
            self.db_manager.update_torrent_file_priorities(info_hash, file_priorities)
            
            logger.info(f"File priorities set successfully for torrent: {info_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set file priorities: {str(e)}")
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