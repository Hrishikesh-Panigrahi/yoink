import libtorrent as lt
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from utils.logger import setup_logger
from pathlib import Path
from core.database_manager import DatabaseManager

# Set up logger
logger = setup_logger('torrent_manager')

@dataclass
class TorrentInfo:
    """Class for storing torrent information"""
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
    added_time: datetime = field(default_factory=datetime.now)
    
    def update_from_handle(self, handle: lt.torrent_handle):
        """Update torrent info from libtorrent handle"""
        try:
            status = handle.status()
            info = handle.get_torrent_info()
            
            if info:
                self.size = self._format_size(info.total_size())
            else:
                self.size = "Unknown"
                
            self.progress = status.progress * 100
            self.download_speed = self._format_speed(status.download_rate)
            self.upload_speed = self._format_speed(status.upload_rate)
            self.seeds = status.num_seeds
            self.peers = status.num_peers
            self.status = self._get_state_string(status.state)
            self.save_path = status.save_path
            self.error = str(status.error) if status.error else ""
            
        except Exception as e:
            logger.error(f"Error updating torrent info: {e}")
            self.error = str(e)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable string"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        elif size_bytes < 1024 * 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024*1024):.1f} GB"
        else:
            return f"{size_bytes/(1024*1024*1024*1024):.1f} TB"
    
    def _format_speed(self, speed_bytes: int) -> str:
        """Format speed in bytes/s to human readable string"""
        if speed_bytes < 1024:
            return f"{speed_bytes} B/s"
        elif speed_bytes < 1024 * 1024:
            return f"{speed_bytes/1024:.1f} KB/s"
        elif speed_bytes < 1024 * 1024 * 1024:
            return f"{speed_bytes/(1024*1024):.1f} MB/s"
        else:
            return f"{speed_bytes/(1024*1024*1024):.1f} GB/s"
    
    def _get_state_string(self, state: int) -> str:
        """Convert libtorrent state to string"""
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

class TorrentManager:
    def __init__(self):
        """Initialize the torrent manager"""
        self.session = lt.session()
        self.torrents = {}  # hash -> (handle, info)
        self.save_path = str(Path.home() / "Downloads")
        self.db_manager = DatabaseManager()
        logger.info(f"Initialized TorrentManager with save path: {self.save_path}")
        
        # Load saved torrents
        self._load_saved_torrents()

    def _load_saved_torrents(self):
        """Load saved torrents from the database"""
        try:
            saved_torrents = self.db_manager.get_all_torrents()
            for torrent in saved_torrents:
                try:
                    # Add torrent to session
                    params = lt.parse_magnet_uri(torrent.magnet_link)
                    params.save_path = torrent.save_path or self.save_path
                    
                    handle = self.session.add_torrent(params)
                    hash = handle.info_hash().to_string()
                    
                    # Create torrent info
                    info = TorrentInfo(
                        name=torrent.name,
                        size="Calculating...",
                        status="Queued"
                    )
                    
                    # Store in memory
                    self.torrents[hash] = (handle, info)
                    logger.info(f"Loaded saved torrent: {info.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading saved torrent {torrent.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error loading saved torrents: {e}")

    def add_torrent(self, magnet_link: str) -> Optional[str]:
        """Add a new torrent from magnet link"""
        try:
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = self.save_path
            
            handle = self.session.add_torrent(params)
            hash = handle.info_hash().to_string()
            
            info = TorrentInfo(
                name=handle.name() or params.name,
                size="Calculating...",
                status="Queued"
            )
            
            # Store in memory
            self.torrents[hash] = (handle, info)
            
            # Save to database
            self.db_manager.add_torrent(
                hash=hash,
                name=info.name,
                magnet_link=magnet_link,
                save_path=self.save_path
            )
            
            logger.info(f"Added torrent: {info.name}")
            return hash
            
        except Exception as e:
            logger.error(f"Error adding torrent: {e}")
            return None

    def get_torrent_info(self, hash: str) -> Optional[TorrentInfo]:
        """Get torrent info by hash"""
        try:
            if hash in self.torrents:
                handle, info = self.torrents[hash]
                info.update_from_handle(handle)
                return info
            return None
        except Exception as e:
            logger.error(f"Error getting torrent info: {e}")
            return None

    def get_all_torrents(self) -> List[Tuple[str, TorrentInfo]]:
        """Get all torrents with their info"""
        try:
            result = []
            for hash, (handle, info) in self.torrents.items():
                info.update_from_handle(handle)
                result.append((hash, info))
            return result
        except Exception as e:
            logger.error(f"Error getting all torrents: {e}")
            return []

    def pause_torrent(self, hash: str) -> bool:
        """Pause a torrent"""
        try:
            if hash in self.torrents:
                handle, _ = self.torrents[hash]
                handle.pause()
                logger.info(f"Paused torrent: {handle.name()}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error pausing torrent: {e}")
            return False

    def resume_torrent(self, hash: str) -> bool:
        """Resume a torrent"""
        try:
            if hash in self.torrents:
                handle, _ = self.torrents[hash]
                handle.resume()
                logger.info(f"Resumed torrent: {handle.name()}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resuming torrent: {e}")
            return False

    def remove_torrent(self, hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent"""
        try:
            if hash in self.torrents:
                handle, info = self.torrents[hash]
                self.session.remove_torrent(handle, int(delete_files))
                del self.torrents[hash]
                
                # Remove from database
                self.db_manager.remove_torrent(hash)
                
                logger.info(f"Removed torrent: {info.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing torrent: {e}")
            return False

    def set_save_path(self, path: str):
        """Set the default save path for new torrents."""
        try:
            self.save_path = path
            # Update save path for existing torrents
            for hash, (handle, _) in self.torrents.items():
                try:
                    handle.move_storage(path)
                except Exception as e:
                    logger.error(f"Error moving torrent {hash} to new path: {e}")
            logger.info(f"Set save path to: {path}")
        except Exception as e:
            logger.error(f"Error setting save path: {e}")

    def get_torrents(self) -> List[TorrentInfo]:
        """Get information about all torrents"""
        try:
            results = []
            for handle in self.torrents.values():
                try:
                    status = handle.status()
                    info = handle.get_torrent_info()
                    
                    # Get torrent state
                    state_str = "Unknown"
                    if status.paused:
                        state_str = "Paused"
                    elif status.errc:
                        state_str = "Error"
                    elif status.is_seeding:
                        state_str = "Seeding"
                    elif status.is_downloading:
                        state_str = "Downloading"
                    elif status.is_finished:
                        state_str = "Finished"
                        
                    # Format size
                    size_bytes = info.total_size()
                    size_str = self._format_size(size_bytes)
                    
                    # Get upload date
                    upload_date = datetime.fromtimestamp(info.creation_date()).strftime('%Y-%m-%d %H:%M:%S')
                    
                    results.append(TorrentInfo(
                        name=handle.name(),
                        size=size_str,
                        seeds=status.num_seeds,
                        peers=status.num_peers,
                        upload_date=upload_date,
                        status=state_str,
                        hash=handle.info_hash().to_string()
                    ))
                except Exception as e:
                    logger.error(f"Error getting torrent info: {str(e)}")
                    continue
                    
            return results
        except Exception as e:
            logger.error(f"Error getting torrents: {str(e)}")
            return []

    def _format_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _get_state_string(self, state: int) -> str:
        state_map = {
            lt.torrent_status.checking_files: "Checking",
            lt.torrent_status.downloading_metadata: "Downloading Metadata",
            lt.torrent_status.downloading: "Downloading",
            lt.torrent_status.finished: "Finished",
            lt.torrent_status.seeding: "Seeding",
            lt.torrent_status.allocating: "Allocating",
            lt.torrent_status.checking_resume_data: "Checking Resume Data"
        }
        return state_map.get(state, "Unknown")
        
    def get_torrent_by_hash(self, hash: str) -> Optional[TorrentInfo]:
        """Get torrent info by hash"""
        try:
            if hash in self.torrents:
                handle, info = self.torrents[hash]
                info.update_from_handle(handle)
                return info
            return None
        except Exception as e:
            logger.error(f"Error getting torrent by hash: {e}")
            return None
        
    def set_save_path(self, path: str):
        """Set the default save path for new torrents."""
        self.save_path = path
        for handle in self.torrents.values():
            handle.move_storage(path) 