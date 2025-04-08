import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLabel, QProgressBar, QMenu, QMessageBox, QStatusBar,
                             QSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
from core.torrent_manager import TorrentManager
from database.database import DatabaseManager
from utils.search import SearchUtil, SearchResult
from .loading_dialog import LoadingDialog
import os
import logging
from PyQt6.QtWidgets import QApplication
from utils.logger import setup_logger
import threading
from utils.loader import Loader

# Set up logger
logger = setup_logger('main_window')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow")
        
        self.setWindowTitle("Torrent App")
        self.setMinimumSize(800, 600)
        
        # Initialize components
        self.search_util = SearchUtil()
        self.torrent_manager = TorrentManager()
        self.db_manager = DatabaseManager()
        self.loader = Loader()
        
        # Connect loader signals
        self.loader.progress_updated.connect(self.update_status)
        self.loader.loading_finished.connect(self.on_loading_finished)
        
        self.setup_ui()
        self.setup_timer()
        
        # Set up API health check timer
        self.api_health_timer = QTimer()
        self.api_health_timer.timeout.connect(self.update_api_health)
        self.api_health_timer.start(10000)  # Check every 10 seconds
        
        # Initial API health check
        self.update_api_health()
        
        logger.info("MainWindow initialization completed")
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Top bar with search and API health
        top_bar = QHBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search torrents...")
        self.search_input.returnPressed.connect(self.search_torrents)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_torrents)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        top_bar.addLayout(search_layout)
        
        # API Health Status with small indicator
        api_health_layout = QHBoxLayout()
        self.api_health_label = QLabel("Checking APIs...")
        self.api_health_label.setStyleSheet("""
            QLabel {
                padding: 2px 5px;
                border-radius: 2px;
                font-size: 12px;
                color: #666;
            }
        """)
        api_health_layout.addWidget(self.api_health_label, alignment=Qt.AlignmentFlag.AlignRight)
        top_bar.addLayout(api_health_layout)
        
        layout.addLayout(top_bar)
        
        # Torrent list table
        self.torrent_table = QTableWidget()
        self.torrent_table.setColumnCount(7)
        self.torrent_table.setHorizontalHeaderLabels(["Name", "Size", "Seeds", "Peers", "Upload Date", "Source", "Status"])
        self.torrent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.torrent_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.torrent_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.torrent_table)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def setup_timer(self):
        """Set up timer for updating torrent list"""
        logger.debug("Setting up update timer")
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_torrent_list)
        self.update_timer.start(5000)  # Refresh every 5 seconds
        
    def update_api_health(self):
        """Update API health status indicator"""
        try:
            healthy_apis = [api for api, status in self.search_util.api_status.items() if status.is_healthy]
            total_apis = len(self.search_util.api_status)
            
            if len(healthy_apis) == total_apis:
                self.api_health_label.setText("All APIs healthy")
                self.api_health_label.setStyleSheet("""
                    QLabel {
                        background-color: #4ade80;
                        color: #064e3b;
                        padding: 2px 5px;
                        border-radius: 2px;
                        font-size: 12px;
                    }
                """)
            elif len(healthy_apis) > 0:
                self.api_health_label.setText(f"{len(healthy_apis)}/{total_apis} APIs healthy")
                self.api_health_label.setStyleSheet("""
                    QLabel {
                        background-color: #fbbf24;
                        color: #92400e;
                        padding: 2px 5px;
                        border-radius: 2px;
                        font-size: 12px;
                    }
                """)
            else:
                self.api_health_label.setText("No APIs available")
                self.api_health_label.setStyleSheet("""
                    QLabel {
                        background-color: #f87171;
                        color: #991b1b;
                        padding: 2px 5px;
                        border-radius: 2px;
                        font-size: 12px;
                    }
                """)
        except Exception as e:
            logger.error(f"Error updating API health status: {str(e)}")
            self.api_health_label.setText("API Status: Error")
            self.api_health_label.setStyleSheet("""
                QLabel {
                    background-color: #f87171;
                    color: #991b1b;
                    padding: 2px 5px;
                    border-radius: 2px;
                    font-size: 12px;
                }
            """)
            
    def search_torrents(self):
        """Search for torrents using the search input"""
        query = self.search_input.text().strip()
        if not query:
            logger.warning("Empty search query")
            return
            
        try:
            logger.info(f"Searching for: {query}")
            self.status_bar.showMessage(f"Searching for '{query}'...")
            
            # Perform search
            results = self.search_util.search_torrents(query)
            
            # Display results
            self.show_search_results(results)
            
            # Update status
            self.status_bar.showMessage(f"Found {len(results)} results for '{query}'")
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            self.status_bar.showMessage("Search failed")
            QMessageBox.critical(self, "Search Error", f"Failed to search: {str(e)}")
            
    def show_search_results(self, results: list[SearchResult]):
        """Display search results in the table"""
        self.torrent_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            self.torrent_table.setItem(row, 0, QTableWidgetItem(result.title))
            self.torrent_table.setItem(row, 1, QTableWidgetItem(result.size))
            self.torrent_table.setItem(row, 2, QTableWidgetItem(str(result.seeds)))
            self.torrent_table.setItem(row, 3, QTableWidgetItem(str(result.leeches)))
            self.torrent_table.setItem(row, 4, QTableWidgetItem(result.upload_date))
            self.torrent_table.setItem(row, 5, QTableWidgetItem(result.source))
            self.torrent_table.setItem(row, 6, QTableWidgetItem("Available"))
            
            # Store magnet link in the item data
            self.torrent_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, result.magnet_link)
            
    def download_selected(self):
        """Download selected torrent"""
        selected_rows = self.torrent_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        title = self.torrent_table.item(row, 0).text()
        magnet = self.torrent_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            logger.info(f"Downloading torrent: {title}")
            self.torrent_manager.add_torrent(magnet)
            self.update_torrent_list()
            self.status_bar.showMessage(f"Downloading: {title}")
        except Exception as e:
            logger.error(f"Error downloading torrent: {str(e)}")
            QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")
            
    def update_torrent_list(self):
        """Update the torrent list with current downloads"""
        try:
            torrents = self.torrent_manager.get_torrents()
            self.torrent_table.setRowCount(len(torrents))
            
            for row, torrent in enumerate(torrents):
                self.torrent_table.setItem(row, 0, QTableWidgetItem(torrent.name))
                self.torrent_table.setItem(row, 1, QTableWidgetItem(torrent.size))
                self.torrent_table.setItem(row, 2, QTableWidgetItem(str(torrent.seeds)))
                self.torrent_table.setItem(row, 3, QTableWidgetItem(str(torrent.peers)))
                self.torrent_table.setItem(row, 4, QTableWidgetItem(torrent.upload_date))
                self.torrent_table.setItem(row, 5, QTableWidgetItem("Local"))
                self.torrent_table.setItem(row, 6, QTableWidgetItem(torrent.status))
                
        except Exception as e:
            logger.error(f"Error updating torrent list: {str(e)}")
            
    def show_context_menu(self, position):
        """Show context menu for torrent actions"""
        menu = QMenu()
        
        pause_action = QAction("Pause", self)
        pause_action.triggered.connect(self.pause_selected_torrent)
        menu.addAction(pause_action)
        
        resume_action = QAction("Resume", self)
        resume_action.triggered.connect(self.resume_selected_torrent)
        menu.addAction(resume_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected_torrent)
        menu.addAction(delete_action)
        
        menu.exec(self.torrent_table.mapToGlobal(position))
        
    def pause_selected_torrent(self):
        """Pause selected torrent"""
        selected_rows = self.torrent_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        name = self.torrent_table.item(row, 0).text()
        
        try:
            logger.info(f"Pausing torrent: {name}")
            self.torrent_manager.pause_torrent(name)
            self.update_torrent_list()
            self.status_bar.showMessage(f"Paused: {name}")
        except Exception as e:
            logger.error(f"Error pausing torrent: {str(e)}")
            QMessageBox.critical(self, "Pause Error", f"Failed to pause: {str(e)}")
            
    def resume_selected_torrent(self):
        """Resume selected torrent"""
        selected_rows = self.torrent_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        name = self.torrent_table.item(row, 0).text()
        
        try:
            logger.info(f"Resuming torrent: {name}")
            self.torrent_manager.resume_torrent(name)
            self.update_torrent_list()
            self.status_bar.showMessage(f"Resumed: {name}")
        except Exception as e:
            logger.error(f"Error resuming torrent: {str(e)}")
            QMessageBox.critical(self, "Resume Error", f"Failed to resume: {str(e)}")
            
    def delete_selected_torrent(self):
        """Delete selected torrent"""
        selected_rows = self.torrent_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        name = self.torrent_table.item(row, 0).text()
        
        try:
            logger.info(f"Deleting torrent: {name}")
            self.torrent_manager.remove_torrent(name)
            self.update_torrent_list()
            self.status_bar.showMessage(f"Deleted: {name}")
        except Exception as e:
            logger.error(f"Error deleting torrent: {str(e)}")
            QMessageBox.critical(self, "Delete Error", f"Failed to delete: {str(e)}")
            
    def format_size(self, bytes: int) -> str:
        """Format size in human-readable format"""
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 * 1024:
            return f"{bytes/1024:.1f} KB"
        else:
            return f"{bytes/(1024*1024):.1f} MB"

    def update_status(self, message: str):
        """Update the status bar with the current message"""
        self.status_bar.showMessage(message)
        
    def on_loading_finished(self):
        """Handle loading finished event"""
        self.status_bar.showMessage("Ready") 