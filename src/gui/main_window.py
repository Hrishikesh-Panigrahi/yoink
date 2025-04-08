from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QLabel, QProgressBar, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from ..core.torrent_manager import TorrentManager
from ..database.database import DatabaseManager
from ..utils.search import SearchUtil
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Torrent App")
        self.setMinimumSize(800, 600)
        
        # Initialize managers
        self.torrent_manager = TorrentManager()
        self.db_manager = DatabaseManager()
        self.search_util = SearchUtil()
        
        # Setup UI
        self.setup_ui()
        
        # Setup timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_torrent_list)
        self.update_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Search section
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search torrents...")
        self.search_input.returnPressed.connect(self.search_torrents)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_torrents)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)
        
        # Torrent list
        self.torrent_table = QTableWidget()
        self.torrent_table.setColumnCount(7)
        self.torrent_table.setHorizontalHeaderLabels([
            "Name", "Size", "Progress", "Seeds", "Peers", "Status", "Speed"
        ])
        self.torrent_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.torrent_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.torrent_table)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def search_torrents(self):
        query = self.search_input.text()
        if not query:
            return
            
        results = self.search_util.search_torrents(query)
        self.show_search_results(results)
        
    def show_search_results(self, results):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Search Results")
        
        # Create a table widget for results
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Name", "Size", "Seeds", "Peers", "Source"
        ])
        
        table.setRowCount(len(results))
        for i, result in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(result.name))
            table.setItem(i, 1, QTableWidgetItem(self.search_util.format_size(result.size)))
            table.setItem(i, 2, QTableWidgetItem(str(result.seeds)))
            table.setItem(i, 3, QTableWidgetItem(str(result.peers)))
            table.setItem(i, 4, QTableWidgetItem(result.source))
            
        dialog.layout().addWidget(table)
        
        # Add download button
        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(lambda: self.download_selected(table))
        dialog.layout().addWidget(download_btn)
        
        dialog.exec()
        
    def download_selected(self, table):
        selected_rows = table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        magnet_link = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if magnet_link:
            self.torrent_manager.add_torrent(magnet_link)
            self.update_torrent_list()
            
    def update_torrent_list(self):
        torrents = self.torrent_manager.get_all_torrents()
        self.torrent_table.setRowCount(len(torrents))
        
        for i, torrent in enumerate(torrents):
            self.torrent_table.setItem(i, 0, QTableWidgetItem(torrent.name))
            self.torrent_table.setItem(i, 1, QTableWidgetItem(self.search_util.format_size(torrent.size)))
            
            progress = QProgressBar()
            progress.setValue(int(torrent.progress))
            self.torrent_table.setCellWidget(i, 2, progress)
            
            self.torrent_table.setItem(i, 3, QTableWidgetItem(str(torrent.num_seeds)))
            self.torrent_table.setItem(i, 4, QTableWidgetItem(str(torrent.num_peers)))
            self.torrent_table.setItem(i, 5, QTableWidgetItem(torrent.state))
            self.torrent_table.setItem(i, 6, QTableWidgetItem(
                f"↓ {self.search_util.format_size(torrent.download_rate)}/s"
            ))
            
    def show_context_menu(self, position):
        menu = QMenu()
        pause_action = menu.addAction("Pause")
        resume_action = menu.addAction("Resume")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(self.torrent_table.mapToGlobal(position))
        
        if action == pause_action:
            self.pause_selected_torrent()
        elif action == resume_action:
            self.resume_selected_torrent()
        elif action == delete_action:
            self.delete_selected_torrent()
            
    def pause_selected_torrent(self):
        selected_items = self.torrent_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            torrent_hash = self.torrent_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if torrent_hash:
                self.torrent_manager.pause_torrent(torrent_hash)
                
    def resume_selected_torrent(self):
        selected_items = self.torrent_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            torrent_hash = self.torrent_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if torrent_hash:
                self.torrent_manager.resume_torrent(torrent_hash)
                
    def delete_selected_torrent(self):
        selected_items = self.torrent_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            torrent_hash = self.torrent_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if torrent_hash:
                self.torrent_manager.remove_torrent(torrent_hash, True) 