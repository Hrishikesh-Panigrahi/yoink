import libtorrent as lt
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from src.utils.logger import setup_logger
from pathlib import Path
from src.database.database import DatabaseManager
import threading
import time
import logging

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
        """Initialize TorrentManager with default settings"""
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()
        
        # Initialize session
        self.session = lt.session()
        
        # Initialize torrents dictionary
        self.torrents = {}  # info_hash -> (torrent, info)
        
        # Set up session settings
        settings = {
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True
        }
        self.session.apply_settings(settings)
        
        # Get default download directory from database
        self.save_path = self.db_manager.get_setting('default_download_dir')
        if not self.save_path:
            self.save_path = os.path.expanduser("~/Downloads")
            self.db_manager.set_setting('default_download_dir', self.save_path)
        
        self.logger.info(f"Initialized TorrentManager with save path: {self.save_path}")
        
        # Load saved torrents
        self._load_saved_torrents()
        
        # Optimize session settings
        self._optimize_session_settings()
        self._setup_bandwidth_management()
        self._optimize_connections()

    def __del__(self):
        """Cleanup when the manager is destroyed"""
        if hasattr(self, 'session_thread'):
            self.session_thread.stop()
            self.session_thread.join(timeout=1.0)

    def _load_saved_torrents(self):
        """Load saved torrents from database"""
        try:
            saved_torrents = self.db_manager.get_all_torrents()
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
        """Add a new torrent from magnet link with optimized settings"""
        try:
            # Parse magnet link
            params = lt.parse_magnet_uri(magnet_link)
            
            # Create add_torrent_params
            atp = lt.add_torrent_params()
            
            # Copy parameters from parsed magnet link
            atp.ti = params.ti
            atp.trackers = params.trackers
            atp.info_hash = params.info_hash
            atp.name = params.name
            
            # Set save path
            atp.save_path = self.save_path
            
            # Set optimized piece selection
            atp.flags |= lt.torrent_flags.sequential_download
            
            # Set per-torrent optimizations in params
            atp.max_connections = 60
            atp.max_uploads = -1
            atp.upload_rate_limit = 0
            atp.download_rate_limit = 0
            
            # Add to session
            handle = self.session.add_torrent(atp)
            
            # Get info hash
            info_hash = str(handle.info_hash())
            
            # Check if torrent already exists
            if info_hash in self.torrents:
                return info_hash
            
            # Create torrent info
            info = TorrentInfo(
                name=atp.name or "Loading...",
                size="Calculating...",
                status="Downloading Metadata",
                save_path=self.save_path
            )
            
            # Store in torrents dictionary
            self.torrents[info_hash] = (handle, info)
            
            # Save to database with required parameters
            self.db_manager.add_torrent(
                name=info.name,
                magnet_link=magnet_link,
                info_hash=info_hash,
                size=0,  # Size will be updated when metadata is received
                save_path=self.save_path
            )
            
            return info_hash
        except Exception as e:
            logger.error(f"Error adding torrent: {e}")
            raise

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
                self.db_manager.remove_torrent(hash)
                
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
            self.db_manager.set_setting('default_download_dir', path)
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

    def _optimize_session_settings(self):
        """Apply optimized session settings for better performance"""
        settings = {
            'active_downloads': -1,  # Unlimited active downloads
            'active_seeds': -1,      # Unlimited active seeds
            'active_limit': -1,      # Unlimited active torrents
            'connections_limit': 500, # Maximum number of connections
            'tick_interval': 100,    # Milliseconds between main ticks
            'cache_size': 1024 * 1024 * 1024,  # 1GB cache
            'disk_io_read_mode': 2,  # Use asynchronous disk I/O
            'disk_io_write_mode': 2, # Use asynchronous disk I/O
            'alert_mask': lt.alert.category_t.all_categories,
            'enable_dht': True,      # Enable DHT
            'enable_lsd': True,      # Enable Local Service Discovery
            'enable_upnp': True,     # Enable UPnP
            'enable_natpmp': True,   # Enable NAT-PMP
            'upload_rate_limit': 0,  # Unlimited upload rate
            'download_rate_limit': 0, # Unlimited download rate
            'dht_max_peers': 500,    # Maximum number of peers to store in DHT
            'dht_max_fail_count': 20, # Maximum number of failed tries
            'dht_max_torrents': 2000, # Maximum number of torrents to track
            'dht_max_dht_items': 2000, # Maximum number of DHT items to store
            'dht_search_branching': 10, # Search branching factor
            'dht_max_peers_reply': 100, # Maximum peers to include in replies
            'dht_restrict_routing_ips': True, # Restrict routing table IPs
            'dht_max_torrent_search_reply': 20 # Maximum torrents in search replies
        }
        self.session.apply_settings(settings)

        # Add well-known DHT bootstrap nodes
        bootstrap_nodes = [
            ("router.bittorrent.com", 6881),
            ("dht.transmissionbt.com", 6881),
            ("router.utorrent.com", 6881)
        ]
        for node in bootstrap_nodes:
            self.session.add_dht_node(node)  # Pass the tuple directly

    def _setup_bandwidth_management(self):
        """Setup bandwidth management settings"""
        settings = {
            'upload_rate_limit': 0,    # Unlimited upload rate
            'download_rate_limit': 0,   # Unlimited download rate
            'connections_limit': 500,   # Maximum number of connections
            'unchoke_slots_limit': 20,  # Number of upload slots
            'mixed_mode_algorithm': 1   # Use rate based choking algorithm
        }
        self.session.apply_settings(settings)

    def _optimize_connections(self):
        """Optimize connection settings for better peer discovery"""
        settings = {
            'connections_limit': 500,
            'connection_speed': 200,
            'peer_connect_timeout': 2,
            'request_timeout': 10,
            'peer_timeout': 20,
            'inactivity_timeout': 20,
            'enable_incoming_utp': True,
            'enable_outgoing_utp': True,
            'enable_incoming_tcp': True,
            'enable_outgoing_tcp': True,
            'max_peerlist_size': 4000,
            'max_paused_peerlist_size': 4000,
            'min_reconnect_time': 2,
            'peer_timeout': 20,
            'max_failcount': 20
        }
        self.session.apply_settings(settings)

    def update_torrent_info(self, handle: lt.torrent_handle) -> TorrentInfo:
        """Update torrent information from handle"""
        try:
            info = TorrentInfo(
                name="Loading...",
                size="Calculating...",
                status="Downloading Metadata",
                save_path=self.save_path
            )
            
            # Get torrent metadata if available
            status = handle.status()
            if status.has_metadata:
                torrent_info = handle.get_torrent_info()
                if torrent_info:
                    info.name = torrent_info.name()
                    info.size = self._format_size(torrent_info.total_size())
            
            # Update status and progress
            info.progress = status.progress * 100
            info.download_speed = self._format_speed(status.download_rate)
            info.upload_speed = self._format_speed(status.upload_rate)
            info.seeds = status.num_seeds
            info.peers = status.num_peers
            info.error = str(status.error) if status.error else ""
            
            # Calculate ETA
            if status.state == lt.torrent_status.downloading and status.download_rate > 0:
                try:
                    torrent_info = handle.get_torrent_info()
                    if torrent_info:
                        remaining_bytes = torrent_info.total_size() * (1 - status.progress)
                        eta_seconds = remaining_bytes / status.download_rate
                        info.eta = self._format_time(eta_seconds)
                    else:
                        info.eta = "Unknown"
                except Exception:
                    info.eta = "Unknown"
            elif status.state == lt.torrent_status.seeding:
                info.eta = "Seeding"
            elif status.state == lt.torrent_status.paused:
                info.eta = "Paused"
            else:
                info.eta = "Unknown"
            
            return info
        except Exception as e:
            logger.error(f"Error updating torrent info: {e}")
            return None

    def get_session_stats(self):
        """Get session statistics"""
        try:
            status = self.session.status()
            return {
                'download_rate': status.download_rate,
                'upload_rate': status.upload_rate,
                'total_download': status.total_download,
                'total_upload': status.total_upload,
                'num_peers': status.num_peers
            }
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return None 