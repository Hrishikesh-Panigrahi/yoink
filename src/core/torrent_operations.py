"""Implementation of torrent operations facade."""

from typing import Dict, Optional, Union
from pathlib import Path

from src.core.interfaces.torrent_operations import ITorrentOperations
from src.core.interfaces.torrent_session import ITorrentSession
from src.database.database import DatabaseManager
from src.core.torrent_adder import TorrentAdder
from src.core.torrent_controller import TorrentController
from src.core.torrent_priority_manager import TorrentPriorityManager
from src.core.torrent_remover import TorrentRemover
from src.utils.logger import setup_logger

logger = setup_logger('torrent_operations')

class TorrentOperations(ITorrentOperations):
    """Facade for torrent operations."""
    
    def __init__(self, session_manager: ITorrentSession, db_manager: DatabaseManager):
        """Initialize torrent operations.
        
        Args:
            session_manager: Manager for the libtorrent session
            db_manager: Manager for database operations
        """
        self.session_manager = session_manager
        self.db_manager = db_manager
        
        # Initialize component classes
        self.adder = TorrentAdder(session_manager, db_manager)
        self.controller = TorrentController(session_manager, db_manager)
        self.priority_manager = TorrentPriorityManager(session_manager, db_manager)
        self.remover = TorrentRemover(session_manager, db_manager)
        
        # Share torrent handles dictionary
        self.torrents = self.adder.torrents
        self.controller.torrents = self.torrents
        self.priority_manager.torrents = self.torrents
        self.remover.torrents = self.torrents
        
        logger.info("TorrentOperations facade initialized")
    
    def add_torrent(self, magnet_link: str, save_path: Optional[str] = None) -> str:
        """Add a torrent via magnet link."""
        return self.adder.add_torrent(magnet_link, save_path)
    
    def add_torrent_file(self, torrent_file_path: Union[str, Path], save_path: Optional[str] = None) -> str:
        """Add a torrent via torrent file."""
        return self.adder.add_torrent_file(torrent_file_path, save_path)
    
    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent."""
        return self.remover.remove_torrent(info_hash, delete_files)
    
    def pause_torrent(self, info_hash: str) -> bool:
        """Pause a torrent."""
        return self.controller.pause_torrent(info_hash)
    
    def resume_torrent(self, info_hash: str) -> bool:
        """Resume a paused torrent."""
        return self.controller.resume_torrent(info_hash)
    
    def set_torrent_priority(self, info_hash: str, priority: int) -> bool:
        """Set the priority of a torrent."""
        return self.priority_manager.set_torrent_priority(info_hash, priority)
    
    def set_file_priorities(self, info_hash: str, file_priorities: Dict[int, int]) -> bool:
        """Set the priorities of individual files in a torrent."""
        return self.priority_manager.set_file_priorities(info_hash, file_priorities) 