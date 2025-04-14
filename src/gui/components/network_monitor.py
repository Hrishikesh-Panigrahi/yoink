"""Network speed monitoring component."""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from utils.logger import setup_logger
from .workers import NetworkSpeedWorker

logger = setup_logger('network_monitor')

class NetworkMonitor:
    """Network speed monitoring component."""
    
    def __init__(self, torrent_manager, speed_label: QLabel):
        """Initialize network monitor.
        
        Args:
            torrent_manager: The torrent manager instance
            speed_label: Label to display network speeds
        """
        self.torrent_manager = torrent_manager
        self.speed_label = speed_label
        self.worker: NetworkSpeedWorker = None
        
        # Set up label
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.speed_label.setStyleSheet("QLabel { color: #666; }")
    
    def start(self):
        """Start network speed monitoring."""
        if self.worker is None:
            self.worker = NetworkSpeedWorker(self.torrent_manager)
            self.worker.speed_updated.connect(self.update_speed_label)
            self.worker.error.connect(self.handle_error)
            self.worker.start()
    
    def stop(self):
        """Stop network speed monitoring."""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
    
    def update_speed_label(self, download_speed: float, upload_speed: float):
        """Update the speed label with current network speeds.
        
        Args:
            download_speed: Download speed in KB/s
            upload_speed: Upload speed in KB/s
        """
        # Format speeds
        dl_speed = self.format_speed(download_speed)
        ul_speed = self.format_speed(upload_speed)
        
        # Update label
        self.speed_label.setText(f"↓ {dl_speed} | ↑ {ul_speed}")
    
    def handle_error(self, error_msg: str):
        """Handle network speed monitoring error.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Network speed error: {error_msg}")
        self.speed_label.setText("Network speed: Error")
    
    @staticmethod
    def format_speed(speed_kb: float) -> str:
        """Format speed in KB/s to human readable string.
        
        Args:
            speed_kb: Speed in KB/s
            
        Returns:
            Formatted speed string
        """
        if speed_kb < 1024:
            return f"{speed_kb:.1f} KB/s"
        elif speed_kb < 1024 * 1024:
            return f"{speed_kb/1024:.1f} MB/s"
        else:
            return f"{speed_kb/(1024*1024):.1f} GB/s" 