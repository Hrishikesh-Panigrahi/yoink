"""Context menu components for the main window."""

from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger('context_menus')

class TorrentContextMenu(QMenu):
    """Context menu for torrent items."""
    
    # Signals
    pause_selected = pyqtSignal()
    resume_selected = pyqtSignal()
    delete_selected = pyqtSignal()
    details_selected = pyqtSignal()
    open_folder_selected = pyqtSignal()
    change_priority_selected = pyqtSignal(int)  # Priority level (0-3)
    
    def __init__(self, torrent_info: dict, parent=None):
        super().__init__(parent)
        self.torrent_info = torrent_info
        self.setup_menu()
    
    def setup_menu(self):
        """Set up the context menu items."""
        # Pause/Resume
        status = self.torrent_info.get('status', '').lower()
        if 'paused' in status:
            resume_action = self.addAction("Resume")
            resume_action.triggered.connect(self.resume_selected)
        else:
            pause_action = self.addAction("Pause")
            pause_action.triggered.connect(self.pause_selected)
        
        self.addSeparator()
        
        # Priority submenu
        priority_menu = QMenu("Priority", self)
        priorities = [
            ("High", 3),
            ("Normal", 2),
            ("Low", 1),
            ("Very Low", 0)
        ]
        
        for label, level in priorities:
            action = priority_menu.addAction(label)
            action.triggered.connect(
                lambda checked, l=level: self.change_priority_selected.emit(l)
            )
        
        self.addMenu(priority_menu)
        
        self.addSeparator()
        
        # Open folder
        open_folder_action = self.addAction("Open Folder")
        open_folder_action.triggered.connect(self.open_folder_selected)
        
        # Show details
        details_action = self.addAction("Show Details")
        details_action.triggered.connect(self.details_selected)
        
        self.addSeparator()
        
        # Delete
        delete_action = self.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected)

class SearchResultContextMenu(QMenu):
    """Context menu for search results."""
    
    # Signals
    download_selected = pyqtSignal()
    details_selected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_menu()
    
    def setup_menu(self):
        """Set up the context menu items."""
        # Download
        download_action = self.addAction("Download")
        download_action.triggered.connect(self.download_selected)
        
        # Show details
        details_action = self.addAction("Show Details")
        details_action.triggered.connect(self.details_selected) 