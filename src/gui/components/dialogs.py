"""Dialog components for the main window."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFormLayout, QCheckBox,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger('dialogs')

class TorrentDetailsDialog(QDialog):
    """Dialog for displaying torrent details."""
    
    def __init__(self, torrent_info: dict, parent=None):
        super().__init__(parent)
        self.torrent_info = torrent_info
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Torrent Details")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info form
        form = QFormLayout()
        
        # Name
        name_label = QLabel(self.torrent_info['name'])
        name_label.setWordWrap(True)
        form.addRow("Name:", name_label)
        
        # Size
        size_label = QLabel(self.format_size(self.torrent_info['size']))
        form.addRow("Size:", size_label)
        
        # Status
        status_label = QLabel(self.torrent_info.get('status', 'Unknown'))
        form.addRow("Status:", status_label)
        
        # Save Path
        path_label = QLabel(self.torrent_info.get('save_path', 'Unknown'))
        path_label.setWordWrap(True)
        form.addRow("Save Path:", path_label)
        
        # Progress
        progress = self.torrent_info.get('progress', 0)
        progress_label = QLabel(f"{progress:.1f}%")
        form.addRow("Progress:", progress_label)
        
        # Download Speed
        dl_speed = self.torrent_info.get('download_speed', 0)
        dl_speed_label = QLabel(self.format_speed(dl_speed))
        form.addRow("Download Speed:", dl_speed_label)
        
        # Upload Speed
        ul_speed = self.torrent_info.get('upload_speed', 0)
        ul_speed_label = QLabel(self.format_speed(ul_speed))
        form.addRow("Upload Speed:", ul_speed_label)
        
        # Peers
        peers = self.torrent_info.get('num_peers', 0)
        peers_label = QLabel(str(peers))
        form.addRow("Peers:", peers_label)
        
        layout.addLayout(form)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
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

class DeleteTorrentDialog(QDialog):
    """Dialog for confirming torrent deletion."""
    
    def __init__(self, torrent_name: str, parent=None):
        super().__init__(parent)
        self.torrent_name = torrent_name
        self.delete_files = False
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Delete Torrent")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Message
        message = QLabel(f"Are you sure you want to delete '{self.torrent_name}'?")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Delete files checkbox
        self.delete_files_checkbox = QCheckBox("Also delete downloaded files")
        layout.addWidget(self.delete_files_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.accept)
        button_layout.addWidget(delete_button)
        
        layout.addLayout(button_layout)
    
    def get_result(self) -> Tuple[bool, bool]:
        """Get the dialog result.
        
        Returns:
            Tuple of (accepted, delete_files)
        """
        return (self.result() == QDialog.DialogCode.Accepted,
                self.delete_files_checkbox.isChecked())

class ChangeDirectoryDialog(QDialog):
    """Dialog for changing download directory."""
    
    def __init__(self, current_dir: str, parent=None):
        super().__init__(parent)
        self.current_dir = current_dir
        self.new_dir = current_dir
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Change Download Directory")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Directory input
        input_layout = QHBoxLayout()
        
        self.dir_input = QLineEdit(self.current_dir)
        input_layout.addWidget(self.dir_input)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_directory)
        input_layout.addWidget(browse_button)
        
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def browse_directory(self):
        """Open directory browser dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            self.current_dir
        )
        if directory:
            self.dir_input.setText(directory)
    
    def get_directory(self) -> Optional[str]:
        """Get the selected directory.
        
        Returns:
            Selected directory path or None if cancelled
        """
        if self.result() == QDialog.DialogCode.Accepted:
            return self.dir_input.text()
        return None 