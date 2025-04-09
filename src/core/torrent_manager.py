import libtorrent as lt
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from utils.logger import setup_logger
from pathlib import Path
from database.database import DatabaseManager
import threading
import time

# Set up logger
logger = setup_logger('torrent_manager')

class SessionThread(threading.Thread):
    """Thread to handle libtorrent session operations"""
    def __init__(self, session: lt.session):
        super().__init__()
        self.session = session
        self.running = True
        self.daemon = True

    def run(self):
        while self.running:
            try:
                self.session.post_torrent_updates()
                time.sleep(0.1)  # Update every 100ms
            except Exception as e:
                logger.error(f"Error in session thread: {e}")
                time.sleep(1)  # Wait longer on error

    def stop(self):
        self.running = False

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
    eta: str = "Unknown"  # Added ETA field
    
    def update_from_handle(self, handle: lt.torrent_handle):
        """Update torrent info from libtorrent handle"""
        try:
            status = handle.status()
            
            # Update status based on metadata and state
            if not handle.has_metadata():
                self.status = "Downloading Metadata"
            elif status.paused:
                self.status = "Paused"
            else:
                self.status = self._get_state_string(status.state)
            
            # Update other fields
            self.progress = status.progress * 100
            self.download_speed = self._format_speed(status.download_rate)
            self.upload_speed = self._format_speed(status.upload_rate)
            self.seeds = status.num_seeds
            self.peers = status.num_peers
            self.save_path = status.save_path
            self.error = str(status.error) if status.error else ""
            
            # Update name and size if we have metadata
            try:
                if handle.has_metadata():
                    info = handle.get_torrent_info()
                    if info:
                        self.name = info.name()
                        self.size = self._format_size(info.total_size())
            except Exception:
                pass  # Keep existing name/size if update fails
            
            # Calculate ETA
            if self.status == "Downloading" and status.download_rate > 0:
                try:
                    info = handle.get_torrent_info()
                    if info:
                        remaining_bytes = info.total_size() * (1 - status.progress)
                        eta_seconds = remaining_bytes / status.download_rate
                        self.eta = self._format_time(eta_seconds)
                    else:
                        self.eta = "Unknown"
                except Exception:
                    self.eta = "Unknown"
            elif self.status == "Seeding":
                self.eta = "Seeding"
            elif self.status == "Paused":
                self.eta = "Paused"
            else:
                self.eta = "Unknown"
            
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

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable string"""
        if seconds < 0 or seconds == float('inf'):
            return "Unknown"
            
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h"
        else:
            days = int(seconds / 86400)
            return f"{days}d"

class TorrentManager:
    def __init__(self):
        """Initialize the torrent manager"""
        self.session = lt.session()
        
        # Configure session settings
        settings = {
            'active_downloads': 4,  # Number of active download threads
            'active_seeds': 0,      # Disable seeding
            'active_limit': 8,      # Total number of active torrents
            'download_rate_limit': 0,  # Download speed limit (0 for unlimited)
            'upload_rate_limit': 0,    # Upload speed limit (0 for unlimited)
            'connections_limit': 200,   # Maximum number of connections
            'alert_mask': lt.alert.category_t.all_categories,  # Enable all alerts
            'enable_dht': True,         # Enable DHT
            'enable_lsd': True,         # Enable Local Service Discovery
            'enable_upnp': True,        # Enable UPnP
            'enable_natpmp': True       # Enable NAT-PMP
        }
        
        # Apply settings to session
        self.session.apply_settings(settings)
        
        # Start DHT, LSD, and UPnP
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
        self.session.start_natpmp()
        
        self.session_thread = SessionThread(self.session)
        self.session_thread.start()
        
        self.torrents = {}  # info_hash -> (torrent, info)
        self.save_path = None
        self.db = DatabaseManager()
        # Set initial save path from database
        self.save_path = self.db.get_default_download_dir()
        logger.info(f"Initialized TorrentManager with save path: {self.save_path}")
        
        # Load saved torrents
        self._load_saved_torrents()

    def __del__(self):
        """Cleanup when the manager is destroyed"""
        if hasattr(self, 'session_thread'):
            self.session_thread.stop()
            self.session_thread.join(timeout=1.0)

    def _load_saved_torrents(self):
        """Load saved torrents from database"""
        try:
            saved_torrents = self.db.get_all_torrents()
            for torrent in saved_torrents:
                try:
                    # Create torrent handle
                    params = lt.add_torrent_params()
                    params.url = torrent.magnet_link
                    params.save_path = torrent.save_path
                    
                    # Add to session
                    handle = self.session.add_torrent(params)
                    
                    # Store in memory
                    info = TorrentInfo(
                        name=torrent.name,
                        size=torrent.size,
                        status=torrent.status,
                        save_path=torrent.save_path
                    )
                    self.torrents[torrent.info_hash] = (handle, info)
                    
                    logger.info(f"Loaded saved torrent: {torrent.name} with save path: {torrent.save_path}")
                except Exception as e:
                    logger.error(f"Error loading saved torrent {torrent.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error loading saved torrents: {e}")
            raise

    def add_torrent(self, magnet_link: str) -> str:
        """Add a new torrent from magnet link"""
        try:
            # Parse magnet link
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = self.save_path
            
            # Add to session
            handle = self.session.add_torrent(params)
            info_hash = str(handle.info_hash())
            
            # Create initial torrent info object with placeholder values
            torrent_info = TorrentInfo(
                name="Loading...",
                size="Calculating...",
                status="Downloading Metadata",
                save_path=self.save_path
            )
            
            # Store in memory
            self.torrents[info_hash] = (handle, torrent_info)
            
            # Save to database with initial values
            self.db.add_torrent(
                name="Loading...",
                magnet_link=magnet_link,
                info_hash=info_hash,
                size=0,
                save_path=self.save_path
            )
            
            logger.info(f"Added torrent with hash: {info_hash}")
            return info_hash
            
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
                handle, info = self.torrents[hash]
                handle.pause()
                # Update the info object's status directly
                info.status = "Paused"
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
                handle, info = self.torrents[hash]
                handle.resume()
                # Update the info object's status directly
                info.status = "Downloading"
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
                self.db.remove_torrent(hash)
                
                logger.info(f"Removed torrent: {info.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing torrent: {e}")
            return False

    def set_save_path(self, path: str):
        """Set the save path for new torrents and update the database setting.
        This only affects new torrents, existing torrents continue with their original paths."""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            self.save_path = path
            self.db.set_setting('default_download_dir', path)
            logger.info(f"Save path updated to: {path} for new downloads")
        except Exception as e:
            logger.error(f"Error setting save path: {e}")
            raise

    def get_torrents(self) -> List[TorrentInfo]:
        """Get information about all torrents"""
        try:
            results = []
            for hash, (handle, info) in self.torrents.items():
                try:
                    info.update_from_handle(handle)
                    results.append(info)
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