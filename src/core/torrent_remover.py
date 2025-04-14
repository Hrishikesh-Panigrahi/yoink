"""Implementation of torrent removal operations."""

import os
import libtorrent as lt
from typing import Optional

from src.core.interfaces.torrent_session import ITorrentSession
from src.database.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger('torrent_remover')

class TorrentRemover:
    """Handles torrent removal operations."""
    
    def __init__(self, session_manager: ITorrentSession, db_manager: DatabaseManager):
        """Initialize torrent remover.
        
        Args:
            session_manager: Manager for the libtorrent session
            db_manager: Manager for database operations
        """
        self.session_manager = session_manager
        self.db_manager = db_manager
        self.session = session_manager.session
        self.torrents = {}  # info_hash -> handle
        
        logger.info("TorrentRemover initialized")
    
    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent.
        
        Args:
            info_hash: The info hash of the torrent to remove
            delete_files: Whether to delete the downloaded files
            
        Returns:
            True if the torrent was removed successfully, False otherwise
        """
        try:
            logger.info(f"Removing torrent: {info_hash}")
            
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found: {info_hash}")
                return False
            
            # Get save path and file information before removing from session
            save_path = handle.status().save_path
            file_paths = []
            
            if delete_files and handle.has_metadata():
                info = handle.get_torrent_info()
                files = info.files()
                for file_idx in range(len(files)):
                    file_path = os.path.join(save_path, files.file_path(file_idx))
                    if os.path.exists(file_path):
                        file_paths.append(file_path)
            
            # Remove from session
            self.session.remove_torrent(handle)
            
            # Remove from database
            self.db_manager.remove_torrent(info_hash)
            
            # Delete files if requested
            if delete_files and file_paths:
                self._delete_files(file_paths, save_path)
            
            # Remove from torrents dictionary
            self.torrents.pop(info_hash.lower(), None)
            
            logger.info(f"Torrent removed successfully: {info_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove torrent: {str(e)}")
            return False
    
    def _delete_files(self, file_paths: list, save_path: str) -> None:
        """Delete the files associated with a torrent.
        
        Args:
            file_paths: List of file paths to delete
            save_path: The directory where the files are saved
        """
        try:
            logger.info(f"Deleting files for torrent in: {save_path}")
            
            # Delete each file
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted file: {file_path}")
            
            # Try to remove the directory if it's empty
            try:
                os.rmdir(save_path)
                logger.debug(f"Removed empty directory: {save_path}")
            except OSError:
                # Directory not empty or doesn't exist
                pass
            
        except Exception as e:
            logger.error(f"Failed to delete files: {str(e)}")
            raise
    
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