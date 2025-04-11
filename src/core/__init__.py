"""Core module for torrent operations and management."""

from src.core.interfaces.torrent_session import ITorrentSession
from src.core.interfaces.torrent_operations import ITorrentOperations
from src.core.interfaces.torrent_info_service import ITorrentInfoService
from src.core.torrent_manager import TorrentManager

__all__ = [
    'ITorrentSession',
    'ITorrentOperations',
    'ITorrentInfoService',
    'TorrentManager',
]
