"""Worker threads for the GUI."""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List
from utils.search import SearchResult
from utils.logger import setup_logger

logger = setup_logger('workers')

class SearchWorker(QThread):
    """Worker thread for searching torrents"""
    finished = pyqtSignal(list, int, int)  # results, total_results, total_pages
    error = pyqtSignal(str)

    def __init__(self, search_util, query: str, page: int = 1):
        super().__init__()
        self.search_util = search_util
        self.query = query
        self.page = page

    def run(self):
        try:
            results, total_results, total_pages = self.search_util.search_torrents(self.query, self.page)
            self.finished.emit(results, total_results, total_pages)
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            self.error.emit(str(e))

class TorrentUpdateWorker(QThread):
    """Worker thread for updating torrent list"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, torrent_manager):
        super().__init__()
        self.torrent_manager = torrent_manager
        self._is_running = True
        self._update_interval = 1000  # 1 second interval

    def run(self):
        while self._is_running:
            try:
                torrents = self.torrent_manager.get_all_torrents()
                self.finished.emit(torrents)
            except Exception as e:
                logger.error(f"Update error: {str(e)}")
                self.error.emit(str(e))
            
            # Sleep for the update interval
            self.msleep(self._update_interval)

    def stop(self):
        """Stop the worker thread"""
        self._is_running = False

    def set_update_interval(self, interval_ms: int):
        """Set the update interval in milliseconds"""
        self._update_interval = interval_ms

class NetworkSpeedWorker(QThread):
    """Worker thread for checking network speed"""
    speed_updated = pyqtSignal(float, float)  # download_speed, upload_speed
    error = pyqtSignal(str)

    def __init__(self, torrent_manager):
        super().__init__()
        self.torrent_manager = torrent_manager
        self._is_running = True

    def run(self):
        while self._is_running:
            try:
                # Get session status
                status = self.torrent_manager.session.status()
                
                # Calculate speeds
                download_speed = status.download_rate / 1024  # Convert to KB/s
                upload_speed = status.upload_rate / 1024     # Convert to KB/s
                
                # Emit speeds
                self.speed_updated.emit(download_speed, upload_speed)
                
            except Exception as e:
                logger.error(f"Network speed error: {str(e)}")
                self.error.emit(str(e))
            
            # Sleep for 1 second
            self.msleep(1000)

    def stop(self):
        """Stop the worker thread"""
        self._is_running = False 