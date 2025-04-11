"""Interface for torrent information services."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TorrentInfo:
    """Data class containing torrent information."""
    name: str
    size: str
    status: str
    progress: float = 0.0
    download_speed: str = "0 KB/s"
    upload_speed: str = "0 KB/s"
    seeds: int = 0
    peers: int = 0
    error: str = ""
    save_path: str = ""
    added_time: datetime = datetime.now()
    eta: str = "Unknown"

class ITorrentInfoService(ABC):
    """Interface for torrent information services.
    
    This interface defines the contract for services that retrieve and manage
    information about torrents, such as status, progress, and file details.
    """
    
    @abstractmethod
    def get_torrent_info(self, info_hash: str) -> Optional[TorrentInfo]:
        """Get information about a specific torrent.
        
        Args:
            info_hash: The info hash of the torrent.
            
        Returns:
            TorrentInfo object if the torrent exists, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_all_torrents(self) -> List[Tuple[str, TorrentInfo]]:
        """Get information about all torrents.
        
        Returns:
            List of tuples containing info hash and TorrentInfo.
        """
        pass
    
    @abstractmethod
    def get_torrent_files(self, info_hash: str) -> List[Dict[str, Any]]:
        """Get information about files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent.
            
        Returns:
            List of dictionaries containing file information.
        """
        pass
    
    @abstractmethod
    def get_torrent_peers(self, info_hash: str) -> List[Dict[str, Any]]:
        """Get information about peers for a torrent.
        
        Args:
            info_hash: The info hash of the torrent.
            
        Returns:
            List of dictionaries containing peer information.
        """
        pass
    
    @abstractmethod
    def update_torrent_info(self, info_hash: str) -> Optional[TorrentInfo]:
        """Update and return the latest information for a torrent.
        
        Args:
            info_hash: The info hash of the torrent.
            
        Returns:
            Updated TorrentInfo object if the torrent exists, None otherwise.
        """
        pass 