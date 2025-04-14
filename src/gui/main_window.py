import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QProgressBar, QComboBox, QSpinBox,
    QDialog, QFormLayout, QCheckBox, QGroupBox,
    QSplitter, QTabWidget, QTextEdit, QMenu, QMenuBar,
    QStatusBar, QToolBar, QStyle, QApplication, QFrame
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize,
    QPoint, QSettings, QUrl
)
from PyQt6.QtGui import (
    QIcon, QAction, QFont, QPalette, QColor,
    QPixmap, QDragEnterEvent, QDropEvent
)

from core.torrent_manager import TorrentManager
from database.database import DatabaseManager
from utils.search import SearchUtil, SearchResult
from utils.loader import Loader
from utils.logger import setup_logger

# Set up logger
logger = setup_logger('main_window')

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
                logger.error(f"Error checking network speed: {e}")
                self.error.emit(str(e))
            
            # Sleep for 1 second before next check
            self.msleep(1000)

    def stop(self):
        """Stop the worker thread"""
        self._is_running = False

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
        
        # Load settings
        self.download_dir = self.load_download_directory()
        
        # Pagination state
        self.current_page = 1
        self.total_pages = 0
        self.total_results = 0
        self.current_query = ""
        
        # Search state
        self.is_searching = False
        self.search_worker = None
        
        # Initialize update worker
        self.update_worker = TorrentUpdateWorker(self.torrent_manager)
        self.update_worker.finished.connect(self.on_update_completed)
        self.update_worker.error.connect(self.on_update_error)
        self.update_worker.start()
        
        # Network speed worker
        self.network_speed_worker = None
        
        # Connect loader signals
        self.loader.progress_updated.connect(self.update_status)
        self.loader.loading_finished.connect(self.on_loading_finished)
        
        # Network speed timer
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.check_network_speed)
        self.speed_timer.start(3000)  # Update every 3 seconds
        
        self.setup_ui()
        
        # Start network speed monitoring
        self.start_network_speed_monitoring()
        
        logger.info("MainWindow initialization completed")
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create top bar for search and network speed
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search bar
        search_bar = QWidget()
        search_bar_layout = QHBoxLayout(search_bar)
        search_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search torrents...")
        self.search_input.returnPressed.connect(self.search_torrents)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_torrents)
        
        search_bar_layout.addWidget(self.search_input)
        search_bar_layout.addWidget(self.search_button)
        
        # Network speed button and label
        network_widget = QWidget()
        network_layout = QHBoxLayout(network_widget)
        network_layout.setContentsMargins(0, 0, 0, 0)
        
        self.network_speed_label = QLabel("Network Speed: Checking...")
        self.network_speed_label.setStyleSheet("""
            QLabel {
                background-color: #f3f4f6;
                color: #374151;
                padding: 3px 6px;
                border-radius: 4px;
                font-size: 10px;
            }
        """)
        
        network_layout.addWidget(self.network_speed_label)
        
        # Add widgets to top bar
        top_bar_layout.addWidget(search_bar)
        top_bar_layout.addWidget(network_widget)
        
        layout.addWidget(top_bar)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Search tab
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        
        # Search results table
        self.search_table = QTableWidget()
        self.search_table.setColumnCount(9)
        self.search_table.setHorizontalHeaderLabels([
            "Title", "Size", "Seeds", "Peers", "Date", "Source", "Magnet", "Quality", "Rating"
        ])
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.search_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.search_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.search_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.search_table.customContextMenuRequested.connect(self.show_search_context_menu)
        self.search_table.cellDoubleClicked.connect(self.download_torrent)
        search_layout.addWidget(self.search_table)
        
        # Add pagination controls
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.previous_page)
        self.prev_button.setEnabled(False)
        
        self.page_label = QLabel("Page 0 of 0")
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        
        search_layout.addWidget(pagination_widget)
        
        # Downloads tab
        downloads_tab = QWidget()
        downloads_layout = QVBoxLayout(downloads_tab)
        
        # Download directory selector
        dir_selector = QWidget()
        dir_layout = QHBoxLayout(dir_selector)
        dir_layout.setContentsMargins(5, 5, 5, 5)
        
        self.dir_label = QLabel(f"Download Directory: {self.download_dir}")
        self.dir_label.setStyleSheet("""
            QLabel {
                background-color: #f8fafc;
                color: #1e293b;
                padding: 6px 10px;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        
        change_dir_button = QPushButton("Change Directory")
        change_dir_button.clicked.connect(self.change_download_directory)
        change_dir_button.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                background-color: #0ea5e9;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
            QPushButton:pressed {
                background-color: #0369a1;
            }
        """)
        
        # Add torrent from file button
        self.add_torrent_button = QPushButton("Add Torrent File")
        self.add_torrent_button.setToolTip("Add a torrent from a .torrent file")
        self.add_torrent_button.clicked.connect(self.add_torrent_from_magnet_file)
        self.add_torrent_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        
        dir_layout.addWidget(self.dir_label, stretch=1)
        dir_layout.addWidget(change_dir_button)
        dir_layout.addWidget(self.add_torrent_button)
        
        downloads_layout.addWidget(dir_selector)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #e2e8f0; margin: 5px 0px;")
        downloads_layout.addWidget(separator)
        
        # Active downloads table
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(9)
        self.downloads_table.setHorizontalHeaderLabels([
            "Name", "Size", "Progress", "Speed", "Seeds", "Peers", "Status", "ETA", "Actions"
        ])
        
        # Set column widths for downloads table
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        self.downloads_table.setColumnWidth(1, 100)  # Size
        self.downloads_table.setColumnWidth(2, 150)  # Progress
        self.downloads_table.setColumnWidth(3, 100)  # Speed
        self.downloads_table.setColumnWidth(4, 60)   # Seeds
        self.downloads_table.setColumnWidth(5, 60)   # Peers
        self.downloads_table.setColumnWidth(6, 100)  # Status
        self.downloads_table.setColumnWidth(7, 80)   # ETA
        self.downloads_table.setColumnWidth(8, 150)  # Actions
        
        self.downloads_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloads_table.customContextMenuRequested.connect(self.show_downloads_context_menu)
        downloads_layout.addWidget(self.downloads_table)
        
        # Add tabs
        self.tab_widget.addTab(search_tab, "Search Results")
        self.tab_widget.addTab(downloads_tab, "Downloads")
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Download Directory: {self.download_dir}")
        
    def batch_update_ui(self):
        """Batch update UI elements to reduce CPU usage"""
        try:
            # Get all torrents
            torrents = self.torrent_manager.get_all_torrents()
            
            # Prepare batch updates
            updates = []
            for hash, info in torrents:
                updates.append({
                    'hash': hash,
                    'progress': info.progress,
                    'speed': info.download_speed,
                    'status': info.status,
                    'seeds': info.seeds,
                    'peers': info.peers,
                    'eta': info.eta
                })
            
            # Apply batch updates
            self.apply_batch_updates(updates)
            
        except Exception as e:
            logger.error(f"Error in batch UI update: {e}")

    def apply_batch_updates(self, updates):
        """Apply batched updates to the UI"""
        try:
            # Update torrent list
            for row in range(self.downloads_table.rowCount()):
                hash_item = self.downloads_table.item(row, 0)
                if hash_item:
                    hash = hash_item.text()
                    update = next((u for u in updates if u['hash'] == hash), None)
                    if update:
                        # Update progress
                        progress_item = self.downloads_table.cellWidget(row, 2)
                        if progress_item:
                            progress_item.setValue(int(update['progress']))
                        
                        # Update speed
                        speed_item = self.downloads_table.item(row, 3)
                        if speed_item:
                            speed_item.setText(update['speed'])
                        
                        # Update status
                        status_item = self.downloads_table.item(row, 6)
                        if status_item:
                            status_item.setText(update['status'])
                        
                        # Update seeds/peers
                        seeds_item = self.downloads_table.item(row, 5)
                        if seeds_item:
                            seeds_item.setText(str(update['seeds']))
                        
                        peers_item = self.downloads_table.item(row, 6)
                        if peers_item:
                            peers_item.setText(str(update['peers']))
                        
                        # Update ETA
                        eta_item = self.downloads_table.item(row, 7)
                        if eta_item:
                            eta_item.setText(update['eta'])
            
        except Exception as e:
            logger.error(f"Error applying batch updates: {e}")

    def search_torrents(self):
        """Search for torrents based on user input."""
        try:
            query = self.search_input.text().strip()
            if not query:
                QMessageBox.warning(self, "Search Error", "Please enter a search query")
                return
            
            logger.info(f"Starting search for: {query}")
            self.current_query = query
            self.current_page = 1
            self.is_searching = True
            self.search_button.setEnabled(False)
            self.search_input.setEnabled(False)
            self.status_bar.showMessage("Searching...")
            
            # Create and start search worker
            self.search_worker = SearchWorker(self.search_util, query)
            self.search_worker.finished.connect(self.on_search_completed)
            self.search_worker.error.connect(self.on_search_error)
            self.search_worker.start()
            
        except Exception as e:
            logger.error(f"Error starting search: {str(e)}")
            self.status_bar.showMessage("Search failed")
            QMessageBox.critical(self, "Search Error", f"Failed to start search: {str(e)}")
            self.is_searching = False
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)

    def on_search_completed(self, results, total_results, total_pages):
        """Handle search completion."""
        try:
            self.total_results = total_results
            self.total_pages = total_pages
            self.show_search_results(results)
            self.update_pagination_controls()
            
            # Update status
            if total_results > 0:
                self.status_bar.showMessage(f"Found {total_results} results")
            else:
                self.status_bar.showMessage("No results found")
            
        except Exception as e:
            logger.error(f"Error handling search results: {str(e)}")
            self.status_bar.showMessage("Error displaying results")
            QMessageBox.critical(self, "Search Error", f"Failed to display results: {str(e)}")
        finally:
            self.is_searching = False
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)

    def on_search_error(self, error_msg):
        """Handle search error."""
        logger.error(f"Search error: {error_msg}")
        self.status_bar.showMessage("Search failed")
        QMessageBox.critical(self, "Search Error", f"Search failed: {error_msg}")
        self.is_searching = False
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)

    def update_torrent_list(self):
        """Update torrent list in background thread"""
        if not self.update_worker or not self.update_worker.isRunning():
            self.update_worker = TorrentUpdateWorker(self.torrent_manager)
            self.update_worker.finished.connect(self.on_update_completed)
            self.update_worker.error.connect(self.on_update_error)
            self.update_worker.start()

    def on_update_completed(self, torrents):
        """Handle torrent list update completion"""
        try:
            if not self.downloads_table.isVisible():
                return  # Skip update if downloads tab is not visible
                
            self.downloads_table.setRowCount(len(torrents))
            
            for row, (hash, torrent) in enumerate(torrents):
                # Always update the row to ensure buttons are refreshed
                self.downloads_table.setItem(row, 0, QTableWidgetItem(torrent.name))
                self.downloads_table.setItem(row, 1, QTableWidgetItem(torrent.size))
                
                # Update progress bar
                progress = QProgressBar()
                progress.setValue(int(torrent.progress))
                progress.setTextVisible(True)
                progress.setFormat(f"{progress.value()}%")
                self.downloads_table.setCellWidget(row, 2, progress)
                
                self.downloads_table.setItem(row, 3, QTableWidgetItem(torrent.download_speed))
                self.downloads_table.setItem(row, 4, QTableWidgetItem(str(torrent.seeds)))
                self.downloads_table.setItem(row, 5, QTableWidgetItem(str(torrent.peers)))
                
                # Update status with color
                status_item = QTableWidgetItem(torrent.status)
                if torrent.status == "Downloading":
                    status_item.setForeground(Qt.GlobalColor.green)
                elif torrent.status == "Paused":
                    status_item.setForeground(Qt.GlobalColor.yellow)
                elif torrent.status == "Seeding":
                    status_item.setForeground(Qt.GlobalColor.blue)
                elif torrent.status == "Finished":
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                elif "Error" in torrent.status:
                    status_item.setForeground(Qt.GlobalColor.red)
                
                # Add tooltip with detailed status info
                tooltip = f"Status: {torrent.status}\n"
                if torrent.error:
                    tooltip += f"Error: {torrent.error}\n"
                tooltip += f"Progress: {torrent.progress:.1f}%\n"
                tooltip += f"Speed: {torrent.download_speed}\n"
                tooltip += f"Seeds: {torrent.seeds}, Peers: {torrent.peers}"
                status_item.setToolTip(tooltip)
                
                self.downloads_table.setItem(row, 6, status_item)
                self.downloads_table.setItem(row, 7, QTableWidgetItem(torrent.eta))
                
                # Always recreate action buttons to ensure they match current status
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                # Add pause/resume button based on status
                if torrent.status == "Downloading":
                    pause_button = QPushButton("Pause")
                    pause_button.clicked.connect(lambda checked, h=hash: self.pause_selected_torrent(h))
                    actions_layout.addWidget(pause_button)
                elif torrent.status == "Paused":
                    resume_button = QPushButton("Resume")
                    resume_button.clicked.connect(lambda checked, h=hash: self.resume_selected_torrent(h))
                    actions_layout.addWidget(resume_button)
                
                # Only show delete button if not checking
                if torrent.status not in ["Checking", "Checking Files", "Checking Resume Data"]:
                    delete_button = QPushButton("Delete")
                    delete_button.clicked.connect(lambda checked, h=hash: self.delete_selected_torrent(h))
                    actions_layout.addWidget(delete_button)
                
                self.downloads_table.setCellWidget(row, 8, actions_widget)
                
        except Exception as e:
            logger.error(f"Error updating downloads table: {e}")

    def on_update_error(self, error_msg):
        """Handle torrent list update error"""
        logger.error(f"Update error: {error_msg}")

    def show_search_results(self, results: List[SearchResult]):
        """Display search results in the table."""
        try:
            # Clear existing rows
            self.search_table.setRowCount(0)
            self.search_table.setRowCount(len(results))
            
            for row, result in enumerate(results):
                try:
                    # Title with quality if available
                    title = result.title
                    title_item = QTableWidgetItem(title)
                    title_item.setToolTip(title)
                    self.search_table.setItem(row, 0, title_item)
                    
                    # Size
                    size_item = QTableWidgetItem(result.size)
                    size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.search_table.setItem(row, 1, size_item)
                    
                    # Seeds
                    seeds_item = QTableWidgetItem(str(result.seeds))
                    seeds_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    seeds_item.setForeground(QColor("#059669"))  # Green color for seeds
                    self.search_table.setItem(row, 2, seeds_item)
                    
                    # Peers
                    peers_item = QTableWidgetItem(str(result.peers))
                    peers_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    peers_item.setForeground(QColor("#DC2626"))  # Red color for peers
                    self.search_table.setItem(row, 3, peers_item)
                    
                    # Date
                    date_item = QTableWidgetItem(result.date)
                    date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.search_table.setItem(row, 4, date_item)
                    
                    # Source with color
                    source_item = QTableWidgetItem(result.source)
                    source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if result.source == "YTS":
                        source_item.setForeground(QColor("#4F46E5"))  # Indigo for YTS
                    else:
                        source_item.setForeground(QColor("#0EA5E9"))  # Sky blue for Pirate Bay
                    self.search_table.setItem(row, 5, source_item)
                    
                    # Store magnet URL
                    magnet_item = QTableWidgetItem()
                    magnet_item.setData(Qt.ItemDataRole.UserRole, result.magnet_url)
                    self.search_table.setItem(row, 6, magnet_item)
                    
                    # Quality
                    if hasattr(result, 'quality') and result.quality:
                        quality_item = QTableWidgetItem(result.quality)
                        quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.search_table.setItem(row, 7, quality_item)
                    
                    # Rating
                    if hasattr(result, 'rating') and result.rating:
                        rating = float(result.rating)
                        if rating > 0:
                            rating_item = QTableWidgetItem(f"{rating:.1f}")
                            rating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            if rating >= 7.0:
                                rating_item.setForeground(QColor("#059669"))  # Green for good ratings
                            elif rating >= 5.0:
                                rating_item.setForeground(QColor("#D97706"))  # Yellow for average ratings
                            else:
                                rating_item.setForeground(QColor("#DC2626"))  # Red for poor ratings
                            self.search_table.setItem(row, 8, rating_item)
                
                except Exception as e:
                    logger.error(f"Error adding row {row}: {e}")
                    continue
            
            # Resize columns to content
            self.search_table.resizeColumnsToContents()
            # Keep title column wider
            self.search_table.setColumnWidth(0, max(self.search_table.columnWidth(0), 300))
            
        except Exception as e:
            logger.error(f"Error showing search results: {e}")
            raise

    def update_pagination_controls(self):
        """Update pagination controls state"""
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
        
        if self.total_pages > 0:
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        else:
            self.page_label.setText("No results")
            
    def previous_page(self):
        """Go to previous page of results"""
        if self.current_page > 1 and not self.is_searching:
            self.current_page -= 1
            self.load_current_page()
            
    def next_page(self):
        """Go to next page of results"""
        if self.current_page < self.total_pages and not self.is_searching:
            self.current_page += 1
            self.load_current_page()
            
    def load_current_page(self):
        """Load the current page of results"""
        if not self.current_query or self.is_searching:
            return
            
        try:
            self.is_searching = True
            self.search_button.setEnabled(False)
            self.search_input.setEnabled(False)
            
            logger.info(f"Loading page {self.current_page} for query: {self.current_query}")
            self.status_bar.showMessage(f"Loading page {self.current_page}...")
            
            # Create and start search worker for the new page
            self.search_worker = SearchWorker(self.search_util, self.current_query, self.current_page)
            self.search_worker.finished.connect(self.on_search_completed)
            self.search_worker.error.connect(self.on_search_error)
            self.search_worker.start()
            
        except Exception as e:
            logger.error(f"Error loading page: {str(e)}")
            self.status_bar.showMessage("Failed to load page")
            QMessageBox.critical(self, "Page Load Error", f"Failed to load page: {str(e)}")
            self.is_searching = False
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)

    def download_torrent(self, row: int):
        """Add torrent to download list"""
        try:
            title = self.search_table.item(row, 0).text()
            magnet = self.search_table.item(row, 6).data(Qt.ItemDataRole.UserRole)
            
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                "Download Confirmation",
                f"Do you want to download {title}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            logger.info(f"Adding torrent to download list: {title}")
            # Set the save path in torrent manager before adding
            self.torrent_manager.set_save_path(self.download_dir)
            hash = self.torrent_manager.add_torrent(magnet)
            
            if hash:
                self.status_bar.showMessage(f"Added to downloads: {title}")
                self.tab_widget.setCurrentIndex(1)  # Switch to downloads tab
                self.update_torrent_list()
            else:
                raise Exception("Failed to add torrent")
                
        except Exception as e:
            logger.error(f"Error adding torrent to downloads: {e}")
            QMessageBox.critical(self, "Download Error", f"Failed to add torrent: {str(e)}")

    def pause_selected_torrent(self, hash: str):
        """Pause selected torrent"""
        try:
            info = self.torrent_manager.get_torrent_info(hash)
            if info:
                logger.info(f"Pausing torrent: {info.name}")
                if self.torrent_manager.pause_torrent(hash):
                    self.status_bar.showMessage(f"Paused: {info.name}")
                    # Force immediate update of the torrent list to show the new status
                    self.update_torrent_list()
                else:
                    raise Exception("Failed to pause torrent")
        except Exception as e:
            logger.error(f"Error pausing torrent: {str(e)}")
            QMessageBox.critical(self, "Pause Error", f"Failed to pause: {str(e)}")
            
    def resume_selected_torrent(self, hash: str):
        """Resume selected torrent"""
        try:
            info = self.torrent_manager.get_torrent_info(hash)
            if info:
                logger.info(f"Resuming torrent: {info.name}")
                if self.torrent_manager.resume_torrent(hash):
                    self.status_bar.showMessage(f"Resumed: {info.name}")
                    # Force immediate update of the torrent list to show the new status
                    self.update_torrent_list()
                else:
                    raise Exception("Failed to resume torrent")
        except Exception as e:
            logger.error(f"Error resuming torrent: {str(e)}")
            QMessageBox.critical(self, "Resume Error", f"Failed to resume: {str(e)}")
            
    def delete_selected_torrent(self, hash: str):
        """Delete selected torrent"""
        try:
            info = self.torrent_manager.get_torrent_info(hash)
            if info:
                # Create a custom message box with options
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Delete Torrent")
                msg_box.setText(f"Do you want to delete {info.name}?")
                
                # Add buttons for the two options
                delete_all_button = msg_box.addButton("Delete Files and Torrent", QMessageBox.ButtonRole.ActionRole)
                delete_torrent_only_button = msg_box.addButton("Delete Torrent Only", QMessageBox.ButtonRole.ActionRole)
                cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                
                # Set default button
                msg_box.setDefaultButton(cancel_button)
                
                # Show the dialog and get the response
                msg_box.exec()
                
                clicked_button = msg_box.clickedButton()
                
                if clicked_button == delete_all_button:
                    # Delete both files and torrent
                    logger.info(f"Deleting torrent and files: {info.name}")
                    if self.torrent_manager.remove_torrent(hash, delete_files=True):
                        self.status_bar.showMessage(f"Deleted torrent and files: {info.name}")
                        self.update_torrent_list()
                    else:
                        raise Exception("Failed to delete torrent and files")
                elif clicked_button == delete_torrent_only_button:
                    # Delete torrent only
                    logger.info(f"Deleting torrent only: {info.name}")
                    if self.torrent_manager.remove_torrent(hash, delete_files=False):
                        self.status_bar.showMessage(f"Deleted torrent only: {info.name}")
                        self.update_torrent_list()
                    else:
                        raise Exception("Failed to delete torrent")
                # If cancel was clicked, do nothing
                
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

    def load_download_directory(self) -> str:
        """Load download directory from settings or use default"""
        try:
            saved_dir = self.db_manager.get_setting("download_directory")
            if saved_dir and os.path.isdir(saved_dir):
                logger.info(f"Loaded saved download directory: {saved_dir}")
                return saved_dir
        except Exception as e:
            logger.error(f"Error loading download directory setting: {e}")
        
        # Use default directory if no saved directory or error
        default_dir = str(Path.home() / "Downloads")
        logger.info(f"Using default download directory: {default_dir}")
        return default_dir

    def change_download_directory(self):
        """Open a dialog to change the download directory"""
        try:
            current_dir = self.torrent_manager.save_path
            new_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Download Directory",
                current_dir,
                QFileDialog.Option.ShowDirsOnly
            )
            
            if new_dir:
                self.torrent_manager.set_save_path(new_dir)
                self.download_dir = new_dir
                # Update the directory label
                self.dir_label.setText(f"Download Directory: {new_dir}")
                # Update the status bar
                self.status_bar.showMessage(f"Download Directory: {new_dir}")
                logger.info(f"Download directory changed to: {new_dir}")
                QMessageBox.information(
                    self,
                    "Success",
                    f"Download directory changed to:\n{new_dir}"
                )
        except Exception as e:
            logger.error(f"Error changing download directory: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to change download directory:\n{str(e)}"
            )

    def view_torrent_details(self, row: int):
        """Show details dialog for selected torrent"""
        title = self.search_table.item(row, 0).text()
        size = self.search_table.item(row, 1).text()
        seeds = self.search_table.item(row, 2).text()
        peers = self.search_table.item(row, 3).text()
        date = self.search_table.item(row, 4).text()
        source = self.search_table.item(row, 5).text()
        
        details = f"""
        Name: {title}
        Size: {size}
        Seeds: {seeds}
        Peers: {peers}
        Upload Date: {date}
        Source: {source}
        """
        
        QMessageBox.information(self, "Torrent Details", details)

    def show_search_context_menu(self, position):
        """Show context menu for search results"""
        menu = QMenu()
        
        view_action = QAction("View", self)
        view_action.triggered.connect(lambda: self.view_torrent_details(position.y()))
        menu.addAction(view_action)
        
        download_action = QAction("Download", self)
        download_action.triggered.connect(lambda: self.download_torrent(position.y()))
        menu.addAction(download_action)
        
        menu.exec(self.search_table.mapToGlobal(position))

    def show_downloads_context_menu(self, position):
        """Show context menu for download actions"""
        menu = QMenu()
        
        # Get the selected row
        row = position.y()
        if row < 0 or row >= self.downloads_table.rowCount():
            return
        
        # Get the torrent hash from the selected row
        hash_item = self.downloads_table.item(row, 0)
        if not hash_item:
            return
            
        hash_str = hash_item.data(Qt.ItemDataRole.UserRole)
        
        pause_action = QAction("Pause", self)
        pause_action.triggered.connect(lambda: self.pause_selected_torrent(hash_str))
        menu.addAction(pause_action)
        
        resume_action = QAction("Resume", self)
        resume_action.triggered.connect(lambda: self.resume_selected_torrent(hash_str))
        menu.addAction(resume_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_selected_torrent(hash_str))
        menu.addAction(delete_action)
        
        menu.exec(self.downloads_table.mapToGlobal(position))

    def check_network_speed(self):
        """Check network speed with reduced frequency"""
        try:
            # Get session status
            status = self.torrent_manager.session.status()
            if status:
                download_speed = status.download_rate / 1024  # Convert to KB/s
                upload_speed = status.upload_rate / 1024     # Convert to KB/s
                
                # Format speeds
                download_str = f"{download_speed:.1f} KB/s" if download_speed < 1024 else f"{download_speed/1024:.1f} MB/s"
                upload_str = f"{upload_speed:.1f} KB/s" if upload_speed < 1024 else f"{upload_speed/1024:.1f} MB/s"
                
                # Update label
                self.network_speed_label.setText(f"↓ {download_str} | ↑ {upload_str}")
                
                # Update style based on speed
                if download_speed > 1024:  # If download speed > 1 MB/s
                    self.network_speed_label.setStyleSheet("""
                        QLabel {
                            background-color: #dcfce7;
                            color: #166534;
                            padding: 3px 6px;
                            border-radius: 4px;
                            font-size: 10px;
                        }
                    """)
                else:
                    self.network_speed_label.setStyleSheet("""
                        QLabel {
                            background-color: #f3f4f6;
                            color: #374151;
                            padding: 3px 6px;
                            border-radius: 4px;
                            font-size: 10px;
                        }
                    """)
            else:
                raise Exception("Failed to get session status")
            
        except Exception as e:
            logger.error(f"Error checking network speed: {e}")
            self.network_speed_label.setText("Network Speed: Error")
            self.network_speed_label.setStyleSheet("""
                QLabel {
                    background-color: #fee2e2;
                    color: #991b1b;
                    padding: 3px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                }
            """)

    def start_network_speed_monitoring(self):
        """Start the network speed monitoring worker"""
        if self.network_speed_worker is None:
            self.network_speed_worker = NetworkSpeedWorker(self.torrent_manager)
            self.network_speed_worker.speed_updated.connect(self.update_network_speed_label)
            self.network_speed_worker.error.connect(self.handle_network_speed_error)
            self.network_speed_worker.start()

    def stop_network_speed_monitoring(self):
        """Stop the network speed monitoring worker"""
        if self.network_speed_worker is not None:
            self.network_speed_worker.stop()
            self.network_speed_worker.wait()

    def update_network_speed_label(self, download_speed: float, upload_speed: float):
        """Update the network speed label with new speeds"""
        # Format speeds
        download_str = f"{download_speed:.1f} KB/s" if download_speed < 1024 else f"{download_speed/1024:.1f} MB/s"
        upload_str = f"{upload_speed:.1f} KB/s" if upload_speed < 1024 else f"{upload_speed/1024:.1f} MB/s"
        
        # Update label
        self.network_speed_label.setText(f"↓ {download_str} | ↑ {upload_str}")
        
        # Update style based on speed
        if download_speed > 1024:  # If download speed > 1 MB/s
            self.network_speed_label.setStyleSheet("""
                QLabel {
                    background-color: #dcfce7;
                    color: #166534;
                    padding: 3px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                }
            """)
        else:
            self.network_speed_label.setStyleSheet("""
                QLabel {
                    background-color: #f3f4f6;
                    color: #374151;
                    padding: 3px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                }
            """)

    def handle_network_speed_error(self, error_msg: str):
        """Handle network speed check errors"""
        logger.error(f"Network speed error: {error_msg}")
        self.network_speed_label.setText("Network Speed: Error")
        self.network_speed_label.setStyleSheet("""
            QLabel {
                background-color: #fee2e2;
                color: #991b1b;
                padding: 3px 6px;
                border-radius: 4px;
                font-size: 10px;
            }
        """)

    def add_torrent_from_magnet_file(self):
        """Open a dialog to select a .torrent file and add the torrent"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Torrent File",
                "",
                "Torrent Files (*.torrent);;All Files (*.*)"
            )
            
            if file_path:
                # Set the save path in torrent manager before adding
                self.torrent_manager.set_save_path(self.download_dir)
                hash = self.torrent_manager.add_torrent_file(file_path)
                
                if hash:
                    self.status_bar.showMessage("Added torrent from file")
                    self.update_torrent_list()
                else:
                    raise Exception("Failed to add torrent")
                    
        except Exception as e:
            logger.error(f"Error adding torrent from file: {e}")
            QMessageBox.critical(
                self,
                "Add Torrent Error",
                f"Failed to add torrent from file:\n{str(e)}"
            )

    def closeEvent(self, event):
        """Handle window close event"""
        # Stop update worker
        if self.update_worker:
            self.update_worker.stop()
            self.update_worker.wait()
        
        # Stop network speed monitoring
        self.stop_network_speed_monitoring()
        
        # Stop timers
        self.speed_timer.stop()
        
        # Accept the close event
        event.accept() 