"""Implementation of the torrent information service."""

import libtorrent as lt
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from src.core.interfaces.torrent_info_service import ITorrentInfoService, TorrentInfo
from src.utils.formatters import format_size, format_speed, format_time
from src.utils.logger import setup_logger

logger = setup_logger('torrent_info_service')

class TorrentInfoService(ITorrentInfoService):
    """Implementation of torrent information service."""
    
    def __init__(self, session):
        """Initialize the torrent information service.
        
        Args:
            session: libtorrent session object
        """
        self.session = session
        self.torrents = {}  # info_hash -> handle
        logger.info("TorrentInfoService initialized")
    
    def get_torrent_info(self, info_hash: str) -> Optional[TorrentInfo]:
        """Get information about a specific torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            TorrentInfo object if the torrent exists, None otherwise
        """
        try:
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle or not handle.is_valid():
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return None
            
            # Update and return torrent info
            return self._create_torrent_info(handle)
            
        except Exception as e:
            logger.error(f"Error getting torrent info: {str(e)}", exc_info=True)
            return None
    
    def get_all_torrents(self) -> List[Tuple[str, TorrentInfo]]:
        """Get information about all torrents.
        
        Returns:
            List of tuples containing info hash and TorrentInfo
        """
        try:
            result = []
            
            # Get all torrents from session
            for handle in self.session.get_torrents():
                if handle.is_valid():
                    info_hash = str(handle.info_hash()).lower()
                    info = self._create_torrent_info(handle)
                    result.append((info_hash, info))
                    
                    # Update internal dictionary
                    self.torrents[info_hash] = handle
            
            logger.debug(f"Retrieved info for {len(result)} torrents")
            return result
            
        except Exception as e:
            logger.error(f"Error getting all torrents: {str(e)}", exc_info=True)
            return []
    
    def get_torrent_files(self, info_hash: str) -> List[Dict[str, Any]]:
        """Get information about files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            List of dictionaries containing file information
        """
        try:
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle or not handle.is_valid():
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return []
            
            # Check if we have metadata
            if not handle.has_metadata():
                logger.warning(f"Torrent doesn't have metadata yet: {info_hash}")
                return []
            
            # Get file information
            result = []
            torrent_info = handle.get_torrent_info()
            file_storage = torrent_info.files()
            file_progress = handle.file_progress()
            file_priorities = handle.file_priorities()
            
            for i in range(torrent_info.num_files()):
                # Get file entry
                file_entry = file_storage.at(i)
                
                # Calculate progress percentage
                progress = 0.0
                if i < len(file_progress) and file_entry.size > 0:
                    progress = (file_progress[i] * 100.0) / file_entry.size
                
                # Get priority
                priority = 0
                if i < len(file_priorities):
                    priority = file_priorities[i]
                
                # Create file info
                file_info = {
                    'index': i,
                    'name': file_entry.path,
                    'size': file_entry.size,
                    'size_str': format_size(file_entry.size),
                    'progress': progress,
                    'priority': priority,
                    'completed': progress >= 100.0
                }
                result.append(file_info)
            
            logger.debug(f"Retrieved info for {len(result)} files in torrent {info_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting torrent files: {str(e)}", exc_info=True)
            return []
    
    def get_torrent_peers(self, info_hash: str) -> List[Dict[str, Any]]:
        """Get information about peers for a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            List of dictionaries containing peer information
        """
        try:
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle or not handle.is_valid():
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return []
            
            # Get peer information
            result = []
            peer_info_list = handle.get_peer_info()
            
            for peer in peer_info_list:
                # Create peer info
                peer_info = {
                    'ip': f"{peer.ip[0]}:{peer.ip[1]}",
                    'client': peer.client,
                    'flags': peer.flags,
                    'download_rate': format_speed(peer.down_speed),
                    'upload_rate': format_speed(peer.up_speed),
                    'progress': peer.progress * 100.0,
                    'seed': peer.seed
                }
                result.append(peer_info)
            
            logger.debug(f"Retrieved info for {len(result)} peers in torrent {info_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting torrent peers: {str(e)}", exc_info=True)
            return []
    
    def update_torrent_info(self, info_hash: str) -> Optional[TorrentInfo]:
        """Update and return the latest information for a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            Updated TorrentInfo object if the torrent exists, None otherwise
        """
        # This is essentially the same as get_torrent_info since that already
        # retrieves the latest information
        return self.get_torrent_info(info_hash)
    
    def _get_handle(self, info_hash: str) -> Optional[lt.torrent_handle]:
        """Get torrent handle by info hash.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            Torrent handle if found, None otherwise
        """
        # Try to get from internal dictionary first
        handle = self.torrents.get(info_hash)
        if handle and handle.is_valid():
            return handle
        
        # Try to find in session
        try:
            sha1_hash = lt.sha1_hash(bytes.fromhex(info_hash))
            handle = self.session.find_torrent(sha1_hash)
            if handle.is_valid():
                # Add to dictionary for future lookups
                self.torrents[info_hash] = handle
                return handle
        except Exception as e:
            logger.error(f"Error getting handle for {info_hash}: {e}")
        
        return None
    
    def _create_torrent_info(self, handle: lt.torrent_handle) -> TorrentInfo:
        """Create TorrentInfo object from torrent handle.
        
        Args:
            handle: Torrent handle
            
        Returns:
            TorrentInfo object
        """
        # Get status
        status = handle.status()
        
        # Default values
        name = "Unknown"
        size = "Unknown"
        torrent_size = 0
        
        # Try to get metadata info
        if handle.has_metadata():
            try:
                info = handle.get_torrent_info()
                name = info.name()
                torrent_size = info.total_size()
                size = format_size(torrent_size)
            except Exception as e:
                logger.error(f"Error getting torrent info: {e}")
        
        # Determine status string
        if not handle.has_metadata():
            status_str = "Downloading Metadata"
        elif status.paused:
            status_str = "Paused"
        else:
            status_str = self._get_state_string(status.state)
        
        # Calculate ETA
        eta = "Unknown"
        if status_str == "Downloading" and status.download_rate > 0:
            try:
                remaining_bytes = torrent_size * (1 - status.progress)
                eta_seconds = remaining_bytes / status.download_rate
                eta = format_time(eta_seconds)
            except Exception:
                eta = "Unknown"
        elif status_str == "Seeding":
            eta = "Seeding"
        elif status_str == "Paused":
            eta = "Paused"
        
        # Create TorrentInfo object
        info = TorrentInfo(
            name=name,
            size=size,
            status=status_str,
            progress=status.progress * 100,
            download_speed=format_speed(status.download_rate),
            upload_speed=format_speed(status.upload_rate),
            seeds=status.num_seeds,
            peers=status.num_peers,
            error=str(status.error) if status.error else "",
            save_path=status.save_path,
            added_time=datetime.now(),  # This should ideally come from the database
            eta=eta
        )
        
        return info
    
    def _get_state_string(self, state: int) -> str:
        """Convert libtorrent state to string.
        
        Args:
            state: libtorrent state value
            
        Returns:
            String representation of state
        """
        states = {
            lt.torrent_status.queued_for_checking: "Queued",
            lt.torrent_status.checking_files: "Checking",
            lt.torrent_status.downloading_metadata: "Downloading Metadata",
            lt.torrent_status.downloading: "Downloading",
            lt.torrent_status.finished: "Finished",
            lt.torrent_status.seeding: "Seeding",
            lt.torrent_status.allocating: "Allocating",
            lt.torrent_status.checking_resume_data: "Checking Resume Data"
        }
        return states.get(state, "Unknown") 