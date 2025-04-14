"""Downloads tab component for the main window."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Dict, Any

from utils.logger import setup_logger
from .workers import TorrentUpdateWorker

logger = setup_logger('downloads_tab')

class DownloadsTab(QWidget):
    """Downloads tab widget."""
    
    # Signals
    torrent_paused = pyqtSignal(str)  # info_hash
    torrent_resumed = pyqtSignal(str)  # info_hash
    torrent_deleted = pyqtSignal(str)  # info_hash
    torrent_details_requested = pyqtSignal(int)  # row index
    
    def __init__(self, torrent_manager, parent=None):
        super().__init__(parent)
        self.torrent_manager = torrent_manager
        self.update_worker: TorrentUpdateWorker = None
        self.torrents: List[Dict[str, Any]] = []
        
        self.setup_ui()
        self.start_update_worker()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_selected)
        toolbar_layout.addWidget(self.pause_button)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_selected)
        toolbar_layout.addWidget(self.resume_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected)
        toolbar_layout.addWidget(self.delete_button)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Downloads table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Size", "Progress", "Status",
            "Download Speed", "Upload Speed", "Peers"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self.on_torrent_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        # Status bar
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
    
    def start_update_worker(self):
        """Start the torrent update worker."""
        self.update_worker = TorrentUpdateWorker(self.torrent_manager)
        self.update_worker.finished.connect(self.on_update_completed)
        self.update_worker.error.connect(self.on_update_error)
        self.update_worker.start()
    
    def stop_update_worker(self):
        """Stop the torrent update worker."""
        if self.update_worker:
            self.update_worker.stop()
            self.update_worker.wait()
    
    def on_update_completed(self, torrents: List[Dict[str, Any]]):
        """Handle torrent list update."""
        self.torrents = torrents
        self.update_table()
    
    def on_update_error(self, error_msg: str):
        """Handle update error."""
        logger.error(f"Update error: {error_msg}")
        self.status_label.setText(f"Error: {error_msg}")
    
    def update_table(self):
        """Update the downloads table."""
        self.table.setRowCount(len(self.torrents))
        
        for row, torrent in enumerate(self.torrents):
            # Name
            name_item = QTableWidgetItem(torrent['name'])
            self.table.setItem(row, 0, name_item)
            
            # Size
            size_item = QTableWidgetItem(self.format_size(torrent['size']))
            self.table.setItem(row, 1, size_item)
            
            # Progress
            progress = torrent.get('progress', 0)
            progress_item = QTableWidgetItem(f"{progress:.1f}%")
            self.table.setItem(row, 2, progress_item)
            
            # Status
            status_item = QTableWidgetItem(torrent.get('status', 'Unknown'))
            self.table.setItem(row, 3, status_item)
            
            # Download Speed
            dl_speed = torrent.get('download_speed', 0)
            dl_speed_item = QTableWidgetItem(self.format_speed(dl_speed))
            self.table.setItem(row, 4, dl_speed_item)
            
            # Upload Speed
            ul_speed = torrent.get('upload_speed', 0)
            ul_speed_item = QTableWidgetItem(self.format_speed(ul_speed))
            self.table.setItem(row, 5, ul_speed_item)
            
            # Peers
            peers = torrent.get('num_peers', 0)
            peers_item = QTableWidgetItem(str(peers))
            self.table.setItem(row, 6, peers_item)
        
        self.update_status()
    
    def update_status(self):
        """Update status label."""
        total = len(self.torrents)
        active = sum(1 for t in self.torrents if t.get('status') == 'downloading')
        self.status_label.setText(f"Total: {total} | Active: {active}")
    
    def pause_selected(self):
        """Pause selected torrent."""
        row = self.table.currentRow()
        if row >= 0 and row < len(self.torrents):
            info_hash = self.torrents[row]['info_hash']
            self.torrent_paused.emit(info_hash)
    
    def resume_selected(self):
        """Resume selected torrent."""
        row = self.table.currentRow()
        if row >= 0 and row < len(self.torrents):
            info_hash = self.torrents[row]['info_hash']
            self.torrent_resumed.emit(info_hash)
    
    def delete_selected(self):
        """Delete selected torrent."""
        row = self.table.currentRow()
        if row >= 0 and row < len(self.torrents):
            info_hash = self.torrents[row]['info_hash']
            self.torrent_deleted.emit(info_hash)
    
    def on_torrent_double_clicked(self, index):
        """Handle double click on a torrent."""
        self.torrent_details_requested.emit(index.row())
    
    def show_context_menu(self, position):
        """Show context menu for downloads table."""
        menu = QMenu()
        
        pause_action = menu.addAction("Pause")
        pause_action.triggered.connect(self.pause_selected)
        
        resume_action = menu.addAction("Resume")
        resume_action.triggered.connect(self.resume_selected)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected)
        
        menu.exec(self.table.mapToGlobal(position))
    
    @staticmethod
    def format_size(bytes: int) -> str:
        """Format size in bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB"
    
    @staticmethod
    def format_speed(bytes_per_sec: int) -> str:
        """Format speed in bytes per second to human readable string."""
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if bytes_per_sec < 1024:
                return f"{bytes_per_sec:.1f} {unit}"
            bytes_per_sec /= 1024
        return f"{bytes_per_sec:.1f} TB/s" 