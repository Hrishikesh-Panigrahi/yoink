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

# Set up logger
logger = setup_logger('main_window')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow")
        self.setWindowTitle("Torrent App")
        self.setMinimumSize(800, 600)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #cbd5e0;
                border-radius: 5px;
                background-color: white;
                font-size: 14px;
                color: #2d3748;
            }
            QLineEdit:focus {
                border-color: #4299e1;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #4299e1;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
            QPushButton:pressed {
                background-color: #2b6cb0;
            }
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                background-color: white;
                gridline-color: #e2e8f0;
            }
            QTableWidget::item {
                padding: 5px;
                color: #2d3748;
            }
            QTableWidget::item:selected {
                background-color: #ebf8ff;
                color: #2c5282;
            }
            QHeaderView::section {
                background-color: #f7fafc;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                font-weight: bold;
                color: #4a5568;
            }
            QProgressBar {
                border: 1px solid #e2e8f0;
                border-radius: 3px;
                text-align: center;
                background-color: #f7fafc;
                color: #2d3748;
            }
            QProgressBar::chunk {
                background-color: #4299e1;
                border-radius: 2px;
            }
            QStatusBar {
                background-color: #f7fafc;
                color: #4a5568;
            }
            QMenu {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #2d3748;
            }
            QMenu::item:selected {
                background-color: #ebf8ff;
                color: #2c5282;
            }
        """)
        
        # Initialize components
        logger.debug("Initializing components")
        self.torrent_manager = TorrentManager()
        self.db_manager = DatabaseManager()
        self.search_util = SearchUtil()
        
        # Pagination state
        self.current_page = 1
        self.total_results = 0
        self.results_per_page = 20
        
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
        """Set up the user interface"""
        logger.debug("Setting up UI components")
        
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
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_torrents)
        search_layout.addWidget(self.search_button)
        
        top_bar.addLayout(search_layout)
        
        # API Health Status with small indicator
        api_health_layout = QHBoxLayout()
        self.api_health_label = QLabel("Checking APIs...")
        self.api_health_label.setStyleSheet("""
            QLabel {
                padding: 2px 5px;
                border-radius: 2px;
                font-size: 10px;
                color: #666;
            }
        """)
        api_health_layout.addWidget(self.api_health_label, alignment=Qt.AlignmentFlag.AlignRight)
        top_bar.addLayout(api_health_layout)
        
        layout.addLayout(top_bar)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.prev_page_btn = QPushButton("Previous")
        self.prev_page_btn.clicked.connect(self.previous_page)
        self.prev_page_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_page_btn)
        
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(self.page_changed)
        pagination_layout.addWidget(self.page_spin)
        
        self.total_pages_label = QLabel("of 1")
        pagination_layout.addWidget(self.total_pages_label)
        
        self.next_page_btn = QPushButton("Next")
        self.next_page_btn.clicked.connect(self.next_page)
        self.next_page_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_page_btn)
        
        self.results_per_page_spin = QSpinBox()
        self.results_per_page_spin.setMinimum(10)
        self.results_per_page_spin.setMaximum(100)
        self.results_per_page_spin.setValue(20)
        self.results_per_page_spin.valueChanged.connect(self.results_per_page_changed)
        pagination_layout.addWidget(QLabel("Results per page:"))
        pagination_layout.addWidget(self.results_per_page_spin)
        
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        # Search results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Name", "Size", "Seeds", "Peers", "Source"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.results_table)
        
        # Download button
        self.download_button = QPushButton("Download Selected")
        self.download_button.clicked.connect(self.download_selected)
        layout.addWidget(self.download_button)
        
        # Active torrents table
        self.torrent_table = QTableWidget()
        self.torrent_table.setColumnCount(5)
        self.torrent_table.setHorizontalHeaderLabels(["Name", "Progress", "Download Speed", "Upload Speed", "Status"])
        self.torrent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.torrent_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.torrent_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.torrent_table)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        logger.debug("UI setup completed")
        
    def setup_timer(self):
        """Set up timer for updating torrent list"""
        logger.debug("Setting up update timer")
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_torrent_list)
        self.update_timer.start(1000)  # Update every second
        
    def update_api_health(self):
        """Update the API health status indicator"""
        try:
            api_status = self.search_util.get_healthy_apis()
            healthy_apis = sum(1 for api in api_status if api.is_healthy)
            total_apis = len(api_status)
            
            if healthy_apis == 0:
                self.api_health_label.setText("No APIs available")
                self.api_health_label.setStyleSheet("""
                    QLabel {
                        padding: 2px 5px;
                        border-radius: 2px;
                        font-size: 10px;
                        color: white;
                        background-color: #ef4444;
                    }
                """)
            elif healthy_apis == total_apis:
                self.api_health_label.setText("All APIs healthy")
                self.api_health_label.setStyleSheet("""
                    QLabel {
                        padding: 2px 5px;
                        border-radius: 2px;
                        font-size: 10px;
                        color: white;
                        background-color: #22c55e;
                    }
                """)
            else:
                self.api_health_label.setText(f"{healthy_apis}/{total_apis} APIs healthy")
                self.api_health_label.setStyleSheet("""
                    QLabel {
                        padding: 2px 5px;
                        border-radius: 2px;
                        font-size: 10px;
                        color: white;
                        background-color: #f59e0b;
                    }
                """)
                
        except Exception as e:
            logger.error(f"Error updating API health status: {str(e)}", exc_info=True)
            self.api_health_label.setText("API Status: Error")
            self.api_health_label.setStyleSheet("""
                QLabel {
                    padding: 2px 5px;
                    border-radius: 2px;
                    font-size: 10px;
                    color: white;
                    background-color: #ef4444;
                }
            """)
            
    def search_torrents(self):
        """Search for torrents"""
        query = self.search_input.text().strip()
        if not query:
            logger.warning("Empty search query")
            QMessageBox.warning(self, "Error", "Please enter a search query")
            return
            
        try:
            # Check if any APIs are available
            api_status = self.search_util.get_healthy_apis()
            healthy_apis = sum(1 for api in api_status if api.is_healthy)
            
            if healthy_apis == 0:
                logger.error("No healthy APIs available")
                QMessageBox.critical(self, "Error", "No search APIs are currently available. Please try again later.")
                return
                
            logger.info(f"Searching for: {query}")
            self.status_bar.showMessage("Searching...")
            
            # Reset pagination
            self.current_page = 1
            self.page_spin.setValue(1)
            
            # Perform search
            results, total = self.search_util.search_torrents(
                query,
                page=self.current_page,
                per_page=self.results_per_page
            )
            
            self.total_results = total
            self.update_pagination_controls()
            self.show_search_results(results)
            
            logger.info(f"Search completed: {len(results)} results found")
            self.status_bar.showMessage(f"Found {total} results")
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")
            self.status_bar.showMessage("Search failed")
            
    def show_search_results(self, results):
        """Display search results in the table"""
        logger.debug(f"Displaying {len(results)} search results")
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(result.name))
            self.results_table.setItem(row, 1, QTableWidgetItem(self.search_util.format_size(result.size)))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result.seeds)))
            self.results_table.setItem(row, 3, QTableWidgetItem(str(result.peers)))
            self.results_table.setItem(row, 4, QTableWidgetItem(result.source))
            
    def update_pagination_controls(self):
        """Update pagination controls based on total results"""
        total_pages = (self.total_results + self.results_per_page - 1) // self.results_per_page
        self.page_spin.setMaximum(max(1, total_pages))
        self.total_pages_label.setText(f"of {total_pages}")
        
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)
        
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.page_spin.setValue(self.current_page)
            self.refresh_search()
            
    def next_page(self):
        """Go to next page"""
        total_pages = (self.total_results + self.results_per_page - 1) // self.results_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.page_spin.setValue(self.current_page)
            self.refresh_search()
            
    def page_changed(self, value):
        """Handle page number change"""
        self.current_page = value
        self.refresh_search()
        
    def results_per_page_changed(self, value):
        """Handle results per page change"""
        self.results_per_page = value
        self.current_page = 1
        self.page_spin.setValue(1)
        self.refresh_search()
        
    def refresh_search(self):
        """Refresh search results for current page"""
        query = self.search_input.text().strip()
        if query:
            try:
                logger.info(f"Refreshing search results for page {self.current_page}")
                results, total = self.search_util.search_torrents(
                    query,
                    page=self.current_page,
                    per_page=self.results_per_page
                )
                self.total_results = total
                self.update_pagination_controls()
                self.show_search_results(results)
            except Exception as e:
                logger.error(f"Error refreshing search: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to refresh search: {str(e)}")
                
    def download_selected(self):
        """Download selected torrents"""
        selected_rows = self.results_table.selectedItems()
        if not selected_rows:
            logger.warning("No torrents selected for download")
            QMessageBox.warning(self, "Error", "Please select torrents to download")
            return
            
        try:
            logger.info("Starting download of selected torrents")
            for item in selected_rows:
                row = item.row()
                name = self.results_table.item(row, 0).text()
                source = self.results_table.item(row, 4).text()
                
                # Find the corresponding SearchResult
                for result in self.current_results:
                    if result.name == name and result.source == source:
                        success = self.torrent_manager.add_torrent(result.magnet_link)
                        if success:
                            logger.info(f"Added torrent: {name}")
                        else:
                            logger.error(f"Failed to add torrent: {name}")
                        break
                        
            self.update_torrent_list()
            logger.info("Download process completed")
        except Exception as e:
            logger.error(f"Download error: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Download failed: {str(e)}")
            
    def update_torrent_list(self):
        """Update the list of active torrents"""
        try:
            torrents = self.torrent_manager.get_all_torrents()
            self.torrent_table.setRowCount(len(torrents))
            
            for row, torrent in enumerate(torrents):
                self.torrent_table.setItem(row, 0, QTableWidgetItem(torrent.name))
                self.torrent_table.setItem(row, 1, QTableWidgetItem(f"{torrent.progress:.1f}%"))
                self.torrent_table.setItem(row, 2, QTableWidgetItem(self.format_speed(torrent.download_rate)))
                self.torrent_table.setItem(row, 3, QTableWidgetItem(self.format_speed(torrent.upload_rate)))
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
            
    def format_speed(self, bytes_per_second: int) -> str:
        """Format speed in human-readable format"""
        if bytes_per_second < 1024:
            return f"{bytes_per_second} B/s"
        elif bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second/1024:.1f} KB/s"
        else:
            return f"{bytes_per_second/(1024*1024):.1f} MB/s" 