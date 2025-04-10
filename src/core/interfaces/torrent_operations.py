"""Interface for torrent operations."""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any, Union
import libtorrent as lt
from pathlib import Path

class ITorrentOperations(ABC):
    """Interface for torrent operations.
    
    This interface defines the contract for operations related to torrents,
    such as adding, removing, pausing, and resuming torrents.
    """
    
    @abstractmethod
    def add_torrent(self, magnet_link: str, save_path: Optional[str] = None) -> str:
        """Add a torrent via magnet link.
        
        Args:
            magnet_link: The magnet link of the torrent to add.
            save_path: The directory to save the downloaded files.
            
        Returns:
            The info hash of the added torrent.
            
        Raises:
            ValueError: If the magnet link is invalid.
        """
        pass
    
    @abstractmethod
    def add_torrent_file(self, torrent_file_path: Union[str, Path], save_path: Optional[str] = None) -> str:
        """Add a torrent via torrent file.
        
        Args:
            torrent_file_path: Path to the .torrent file.
            save_path: The directory to save the downloaded files.
            
        Returns:
            The info hash of the added torrent.
            
        Raises:
            ValueError: If the torrent file is invalid.
            FileNotFoundError: If the torrent file does not exist.
        """
        pass
    
    @abstractmethod
    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent.
        
        Args:
            info_hash: The info hash of the torrent to remove.
            delete_files: Whether to delete the downloaded files.
            
        Returns:
            True if the torrent was removed successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def pause_torrent(self, info_hash: str) -> bool:
        """Pause a torrent.
        
        Args:
            info_hash: The info hash of the torrent to pause.
            
        Returns:
            True if the torrent was paused successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def resume_torrent(self, info_hash: str) -> bool:
        """Resume a paused torrent.
        
        Args:
            info_hash: The info hash of the torrent to resume.
            
        Returns:
            True if the torrent was resumed successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def set_torrent_priority(self, info_hash: str, priority: int) -> bool:
        """Set the priority of a torrent.
        
        Args:
            info_hash: The info hash of the torrent.
            priority: The priority value (0-7, where 7 is highest).
            
        Returns:
            True if the priority was set successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def set_file_priorities(self, info_hash: str, file_priorities: Dict[int, int]) -> bool:
        """Set the priorities of individual files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent.
            file_priorities: Dictionary mapping file indices to priority values.
            
        Returns:
            True if the priorities were set successfully, False otherwise.
        """
        pass 