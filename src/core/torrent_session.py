"""Implementation of the torrent session manager."""

import libtorrent as lt
import logging
import threading
import time
from typing import Dict, Any, Optional

from src.core.interfaces.torrent_session import ITorrentSession
from src.utils.logger import setup_logger

logger = setup_logger('torrent_session')

class SessionThread(threading.Thread):
    """Thread to handle libtorrent session operations."""
    
    def __init__(self, session: lt.session):
        """Initialize session thread.
        
        Args:
            session: libtorrent session to manage
        """
        super().__init__()
        self.session = session
        self.running = True
        self.daemon = True
        logger.debug("Session thread initialized")

    def run(self):
        """Run the session thread to process torrent updates."""
        logger.info("Session thread started")
        while self.running:
            try:
                self.session.post_torrent_updates()
                time.sleep(0.1)  # Update every 100ms
            except Exception as e:
                logger.error(f"Error in session thread: {e}")
                time.sleep(1)  # Wait longer on error

    def stop(self):
        """Stop the session thread."""
        logger.info("Stopping session thread")
        self.running = False


class TorrentSession(ITorrentSession):
    """Implementation of the torrent session manager."""
    
    def __init__(self):
        """Initialize the torrent session."""
        self.session = lt.session()
        self.session_thread: Optional[SessionThread] = None
        self.default_settings = {
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'alert_mask': lt.alert.category_t.all_categories
        }
        logger.info("TorrentSession initialized")
    
    def start_session(self) -> None:
        """Start the torrent session."""
        # Apply default settings
        self.apply_settings(self.default_settings)
        
        # Start the session thread
        self.session_thread = SessionThread(self.session)
        self.session_thread.start()
        
        # Initialize DHT and other protocols
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
        self.session.start_natpmp()
        
        logger.info("Torrent session started")
    
    def stop_session(self) -> None:
        """Stop the torrent session."""
        logger.info("Stopping torrent session")
        
        # Stop the session thread
        if self.session_thread:
            self.session_thread.stop()
            self.session_thread.join(timeout=2.0)
            self.session_thread = None
        
        # Stop DHT and other protocols
        self.session.stop_dht()
        self.session.stop_lsd()
        self.session.stop_upnp()
        self.session.stop_natpmp()
        
        logger.info("Torrent session stopped")
    
    def apply_settings(self, settings: Dict[str, Any]) -> None:
        """Apply settings to the session.
        
        Args:
            settings: Dictionary of settings to apply.
        """
        logger.debug(f"Applying session settings: {settings}")
        self.session.apply_settings(settings)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics.
        
        Returns:
            Dictionary of session statistics.
        """
        status = self.session.status()
        return {
            'download_rate': status.download_rate,
            'upload_rate': status.upload_rate,
            'total_download': status.total_download,
            'total_upload': status.total_upload,
            'num_peers': status.num_peers,
            'dht_nodes': status.dht_nodes,
        }
    
    def set_download_limit(self, limit_kbps: int) -> None:
        """Set download bandwidth limit.
        
        Args:
            limit_kbps: Download limit in kilobytes per second.
        """
        logger.info(f"Setting download limit to {limit_kbps} KB/s")
        settings = {
            'download_rate_limit': limit_kbps * 1024,  # Convert to bytes/sec
        }
        self.session.apply_settings(settings)
    
    def set_upload_limit(self, limit_kbps: int) -> None:
        """Set upload bandwidth limit.
        
        Args:
            limit_kbps: Upload limit in kilobytes per second.
        """
        logger.info(f"Setting upload limit to {limit_kbps} KB/s")
        settings = {
            'upload_rate_limit': limit_kbps * 1024,  # Convert to bytes/sec
        }
        self.session.apply_settings(settings)
    
    def optimize_connections(self) -> None:
        """Optimize connections for the session."""
        logger.info("Optimizing session connections")
        
        # Apply optimized connection settings
        settings = {
            'connections_limit': 200,  # Maximum number of connections
            'connection_speed': 20,    # Number of connections per second to try to make
            'peer_connect_timeout': 15,  # Seconds to wait for a peer to respond
            'request_timeout': 20,       # Seconds to wait for a block request
            'peer_timeout': 120,         # Seconds to keep a peer connected without any data
            'close_redundant_connections': True,
        }
        self.session.apply_settings(settings) 