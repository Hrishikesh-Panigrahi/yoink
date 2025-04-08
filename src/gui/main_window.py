import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLabel, QProgressBar, QMenu, QMessageBox, QStatusBar,
                             QSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
from core.torrent_manager import TorrentManager
from database.database import DatabaseManager
from utils.search import SearchUtil
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
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize components
        self.search_util = SearchUtil()
        self.torrent_manager = TorrentManager()
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
        self.torrent_table.setColumnCount(5)
        self.torrent_table.setHorizontalHeaderLabels(["Name", "Size", "Seeds", "Peers", "Source"])
        self.torrent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.torrent_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.torrent_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.torrent_table)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def setup_timer(self):
        """Set up timer for updating torrent list"""
        logger.debug("Setting up update timer")
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_torrent_list)
        self.update_timer.start(1000)  # Update every second
        
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
            QMessageBox.warning(self, "Warning", "Please enter a search query")
            return
            
        logger.info(f"Searching for: {query}")
        
        # Disable search controls
        self.search_input.setEnabled(False)
        self.search_button.setEnabled(False)
        
        # Clear previous results
        self.torrent_table.setRowCount(0)
        
        # Start the loader
        self.loader.start("Searching torrents...")
        
        try:
            # Start search in a separate thread
            self.search_util.search_torrents(
                query,
                on_progress=self.loader.update,
                on_complete=self.show_search_results
            )
        except Exception as e:
            logger.error(f"Error starting search: {str(e)}")
            self.loader.stop()
            self.search_input.setEnabled(True)
            self.search_button.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Failed to start search: {str(e)}")
            
    def show_search_results(self, results):
        """Display search results in the table"""
        try:
            if not results:
                logger.warning("No search results found")
                QMessageBox.information(self, "No Results", "No torrents found matching your search.")
                return
                
            logger.info(f"Found {len(results)} search results")
            
            # Clear previous results
            self.torrent_table.setRowCount(0)
            
            # Add new results
            for result in results:
                row = self.torrent_table.rowCount()
                self.torrent_table.insertRow(row)
                
                # Name
                name_item = QTableWidgetItem(result.name)
                name_item.setToolTip(result.name)
                self.torrent_table.setItem(row, 0, name_item)
                
                # Size
                size_item = QTableWidgetItem(self.search_util.format_size(result.size))
                self.torrent_table.setItem(row, 1, size_item)
                
                # Seeds
                seeds_item = QTableWidgetItem(str(result.seeds))
                self.torrent_table.setItem(row, 2, seeds_item)
                
                # Peers
                peers_item = QTableWidgetItem(str(result.peers))
                self.torrent_table.setItem(row, 3, peers_item)
                
                # Source
                source_item = QTableWidgetItem(result.source)
                self.torrent_table.setItem(row, 4, source_item)
                
                # Store magnet link in the item data
                name_item.setData(Qt.ItemDataRole.UserRole, result.magnet_link)
                
            # Update status bar
            self.status_bar.showMessage(f"Found {len(results)} results")
            
        except Exception as e:
            logger.error(f"Error displaying search results: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to display results: {str(e)}")
            
        finally:
            # Stop the loader and re-enable search controls
            self.loader.stop()
            self.search_input.setEnabled(True)
            self.search_button.setEnabled(True)
        
    def update_torrent_list(self):
        """Update the list of active torrents"""
        try:
            torrents = self.torrent_manager.get_all_torrents()
            self.torrent_table.setRowCount(len(torrents))
            
            for row, torrent in enumerate(torrents):
                self.torrent_table.setItem(row, 0, QTableWidgetItem(torrent.name))
                self.torrent_table.setItem(row, 1, QTableWidgetItem(self.format_size(torrent.size)))
                self.torrent_table.setItem(row, 2, QTableWidgetItem(str(torrent.seeds)))
                self.torrent_table.setItem(row, 3, QTableWidgetItem(str(torrent.peers)))
                self.torrent_table.setItem(row, 4, QTableWidgetItem(torrent.state))
        except Exception as e:
            logger.error(f"Error updating torrent list: {str(e)}", exc_info=True)
            
    def show_context_menu(self, position):
        """Show context menu for torrent operations"""
        try:
            menu = QMenu()
            
            # Get the table that triggered the context menu
            table = self.sender()
            if table == self.torrent_table:
                selected_rows = table.selectedItems()
                if selected_rows:
                    row = selected_rows[0].row()
                    torrent_hash = self.torrent_manager.get_all_torrents()[row].hash
                    
                    pause_action = QAction("Pause", self)
                    pause_action.triggered.connect(lambda: self.pause_selected_torrent(torrent_hash))
                    menu.addAction(pause_action)
                    
                    resume_action = QAction("Resume", self)
                    resume_action.triggered.connect(lambda: self.resume_selected_torrent(torrent_hash))
                    menu.addAction(resume_action)
                    
                    delete_action = QAction("Delete", self)
                    delete_action.triggered.connect(lambda: self.delete_selected_torrent(torrent_hash))
                    menu.addAction(delete_action)
                    
                    menu.exec(table.viewport().mapToGlobal(position))
        except Exception as e:
            logger.error(f"Error showing context menu: {str(e)}", exc_info=True)
            
    def pause_selected_torrent(self, torrent_hash: str):
        """Pause the selected torrent"""
        try:
            logger.info(f"Pausing torrent: {torrent_hash}")
            if self.torrent_manager.pause_torrent(torrent_hash):
                self.update_torrent_list()
                logger.info("Torrent paused successfully")
            else:
                logger.warning(f"Failed to pause torrent: {torrent_hash}")
        except Exception as e:
            logger.error(f"Error pausing torrent: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to pause torrent: {str(e)}")
            
    def resume_selected_torrent(self, torrent_hash: str):
        """Resume the selected torrent"""
        try:
            logger.info(f"Resuming torrent: {torrent_hash}")
            if self.torrent_manager.resume_torrent(torrent_hash):
                self.update_torrent_list()
                logger.info("Torrent resumed successfully")
            else:
                logger.warning(f"Failed to resume torrent: {torrent_hash}")
        except Exception as e:
            logger.error(f"Error resuming torrent: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to resume torrent: {str(e)}")
            
    def delete_selected_torrent(self, torrent_hash: str):
        """Delete the selected torrent"""
        try:
            logger.info(f"Deleting torrent: {torrent_hash}")
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                "Are you sure you want to delete this torrent?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.torrent_manager.remove_torrent(torrent_hash, True):
                    self.update_torrent_list()
                    logger.info("Torrent deleted successfully")
                else:
                    logger.warning(f"Failed to delete torrent: {torrent_hash}")
        except Exception as e:
            logger.error(f"Error deleting torrent: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to delete torrent: {str(e)}")
            
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