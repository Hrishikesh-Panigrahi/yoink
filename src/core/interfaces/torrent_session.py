"""Interface for torrent session management."""

from abc import ABC, abstractmethod
from typing import Dict, Any

class ITorrentSession(ABC):
    """Interface for torrent session management.
    
    This interface defines the contract for managing the libtorrent session,
    including session settings, bandwidth management, and connection optimization.
    """
    
    @abstractmethod
    def start_session(self) -> None:
        """Start the torrent session."""
        pass
    
    @abstractmethod
    def stop_session(self) -> None:
        """Stop the torrent session."""
        pass
    
    @abstractmethod
    def apply_settings(self, settings: Dict[str, Any]) -> None:
        """Apply settings to the session.
        
        Args:
            settings: Dictionary of settings to apply.
        """
        pass
    
    @abstractmethod
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics.
        
        Returns:
            Dictionary of session statistics.
        """
        pass
    
    @abstractmethod
    def set_download_limit(self, limit_kbps: int) -> None:
        """Set download bandwidth limit.
        
        Args:
            limit_kbps: Download limit in kilobytes per second.
        """
        pass
    
    @abstractmethod
    def set_upload_limit(self, limit_kbps: int) -> None:
        """Set upload bandwidth limit.
        
        Args:
            limit_kbps: Upload limit in kilobytes per second.
        """
        pass
    
    @abstractmethod
    def optimize_connections(self) -> None:
        """Optimize connections for the session."""
        pass 