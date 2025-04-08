import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLabel, QProgressBar, QMenu, QMessageBox, QStatusBar,
                             QSpinBox, QTabWidget, QFileDialog, QDialog)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
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

    def run(self):
        try:
            torrents = self.torrent_manager.get_all_torrents()
            self.finished.emit(torrents)
        except Exception as e:
            self.error.emit(str(e))

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
        self.update_worker = None
        
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
        
        # Download directory button
        self.download_dir_button = QPushButton("Set Download Directory")
        self.download_dir_button.clicked.connect(self.set_download_directory)
        top_bar.addWidget(self.download_dir_button)
        
        # API Health Status
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
        
        # Tab widget for search results and downloads
        self.tab_widget = QTabWidget()
        
        # Search results tab
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        self.page_label = QLabel("Page 0 of 0")
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        search_layout.addLayout(pagination_layout)
        
        # Search results table
        self.search_table = QTableWidget()
        self.search_table.setColumnCount(7)
        self.search_table.setHorizontalHeaderLabels(["Name", "Size", "Seeds", "Peers", "Upload Date", "Source", "Actions"])
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.search_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.search_table.customContextMenuRequested.connect(self.show_search_context_menu)
        search_layout.addWidget(self.search_table)
        
        # Downloads tab
        downloads_tab = QWidget()
        downloads_layout = QVBoxLayout(downloads_tab)
        
        # Active downloads table
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(8)
        self.downloads_table.setHorizontalHeaderLabels(["Name", "Size", "Progress", "Speed", "Seeds", "Peers", "Status", "Actions"])
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
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
        
    def setup_timer(self):
        """Set up timer for updating torrent list"""
        logger.debug("Setting up update timer")
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_torrent_list)
        self.update_timer.start(2000)  # Refresh every 2 seconds
        
    def update_api_health(self):
        """Update API health status indicator"""
        try:
            # Get API status from search util
            api_status = self.search_util.get_api_status()
            healthy_apis = [api for api, status in api_status.items() if status]
            total_apis = len(api_status)
            
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
        """Search for torrents in background thread"""
        if self.is_searching:
            return

        query = self.search_input.text().strip()
        if not query:
            self.status_bar.showMessage("Please enter a search query")
            return

        logger.info(f"Searching for: {query}")
        self.current_query = query
        self.is_searching = True
        self.search_button.setEnabled(False)
        self.status_bar.showMessage("Searching...")

        # Create and start search worker
        self.search_worker = SearchWorker(self.search_util, query, self.current_page)
        self.search_worker.finished.connect(self.on_search_completed)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()

    def on_search_completed(self, results, total_results, total_pages):
        """Handle search completion"""
        self.is_searching = False
        self.search_button.setEnabled(True)
        self.total_results = total_results
        self.total_pages = total_pages
        self.show_search_results(results)
        self.update_pagination_controls()
        self.status_bar.showMessage(f"Found {total_results} results")

    def on_search_error(self, error_msg):
        """Handle search error"""
        self.is_searching = False
        self.search_button.setEnabled(True)
        self.status_bar.showMessage(f"Search error: {error_msg}")
        logger.error(f"Search error: {error_msg}")

    def update_torrent_list(self):
        """Update torrent list in background thread"""
        # Create and start update worker
        self.update_worker = TorrentUpdateWorker(self.torrent_manager)
        self.update_worker.finished.connect(self.on_update_completed)
        self.update_worker.error.connect(self.on_update_error)
        self.update_worker.start()

    def on_update_completed(self, torrents):
        """Handle torrent list update completion"""
        try:
            self.downloads_table.setRowCount(len(torrents))
            
            for row, (hash, torrent) in enumerate(torrents):
                self.downloads_table.setItem(row, 0, QTableWidgetItem(torrent.name))
                self.downloads_table.setItem(row, 1, QTableWidgetItem(torrent.size))
                
                # Add progress bar
                progress = QProgressBar()
                progress.setValue(int(torrent.progress))
                progress.setTextVisible(True)
                progress.setFormat(f"{progress.value()}%")
                self.downloads_table.setCellWidget(row, 2, progress)
                
                self.downloads_table.setItem(row, 3, QTableWidgetItem(torrent.download_speed))
                self.downloads_table.setItem(row, 4, QTableWidgetItem(str(torrent.seeds)))
                self.downloads_table.setItem(row, 5, QTableWidgetItem(str(torrent.peers)))
                self.downloads_table.setItem(row, 6, QTableWidgetItem(torrent.status))
                
                # Add action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                if torrent.status == "Downloading":
                    pause_button = QPushButton("Pause")
                    pause_button.clicked.connect(lambda checked, h=hash: self.pause_selected_torrent(h))
                    actions_layout.addWidget(pause_button)
                elif torrent.status == "Paused":
                    resume_button = QPushButton("Resume")
                    resume_button.clicked.connect(lambda checked, h=hash: self.resume_selected_torrent(h))
                    actions_layout.addWidget(resume_button)
                
                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(lambda checked, h=hash: self.delete_selected_torrent(h))
                actions_layout.addWidget(delete_button)
                
                self.downloads_table.setCellWidget(row, 7, actions_widget)
                
        except Exception as e:
            logger.error(f"Error updating downloads table: {e}")

    def on_update_error(self, error_msg):
        """Handle torrent list update error"""
        logger.error(f"Update error: {error_msg}")

    def show_search_results(self, results: list[SearchResult]):
        """Display search results in the table"""
        self.search_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            self.search_table.setItem(row, 0, QTableWidgetItem(result.title))
            self.search_table.setItem(row, 1, QTableWidgetItem(result.size))
            self.search_table.setItem(row, 2, QTableWidgetItem(str(result.seeds)))
            self.search_table.setItem(row, 3, QTableWidgetItem(str(result.leeches)))
            self.search_table.setItem(row, 4, QTableWidgetItem(result.upload_date))
            self.search_table.setItem(row, 5, QTableWidgetItem(result.source))
            
            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            view_button = QPushButton("View")
            view_button.clicked.connect(lambda checked, r=row: self.view_torrent_details(r))
            download_button = QPushButton("Download")
            download_button.clicked.connect(lambda checked, r=row: self.download_torrent(r))
            
            actions_layout.addWidget(view_button)
            actions_layout.addWidget(download_button)
            self.search_table.setCellWidget(row, 6, actions_widget)
            
            # Store magnet link in the item data
            self.search_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, result.magnet_link)
            
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
            
            self.load_current_page_results()
            
            self.update_pagination_controls()
            self.status_bar.showMessage(f"Page {self.current_page} of {self.total_pages}")
            
        except Exception as e:
            logger.error(f"Error loading page: {str(e)}")
            self.status_bar.showMessage("Failed to load page")
            QMessageBox.critical(self, "Page Load Error", f"Failed to load page: {str(e)}")
            
        finally:
            self.is_searching = False
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)
            
    def load_current_page_results(self):
        """Load the current page of results"""
        if not self.current_query or self.is_searching:
            return
            
        try:
            self.is_searching = True
            self.search_button.setEnabled(False)
            self.search_input.setEnabled(False)
            
            logger.info(f"Loading page {self.current_page} for query: {self.current_query}")
            self.status_bar.showMessage(f"Loading page {self.current_page}...")
            
            results, _, _ = self.search_util.search_torrents(self.current_query, self.current_page)
            self.show_search_results(results)
            
            self.update_pagination_controls()
            self.status_bar.showMessage(f"Page {self.current_page} of {self.total_pages}")
            
        except Exception as e:
            logger.error(f"Error loading page: {str(e)}")
            self.status_bar.showMessage("Failed to load page")
            QMessageBox.critical(self, "Page Load Error", f"Failed to load page: {str(e)}")
            
        finally:
            self.is_searching = False
            self.search_button.setEnabled(True)
            self.search_input.setEnabled(True)
            
    def download_torrent(self, row: int):
        """Add torrent to download list"""
        try:
            title = self.search_table.item(row, 0).text()
            magnet = self.search_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
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
                reply = QMessageBox.question(
                    self,
                    "Delete Torrent",
                    f"Do you want to delete {info.name}?\nThis will also delete the downloaded files.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    logger.info(f"Deleting torrent: {info.name}")
                    if self.torrent_manager.remove_torrent(hash, delete_files=True):
                        self.status_bar.showMessage(f"Deleted: {info.name}")
                        self.update_torrent_list()
                    else:
                        raise Exception("Failed to delete torrent")
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
        """Load the download directory from settings"""
        try:
            return self.torrent_manager.save_path
        except Exception as e:
            logger.error(f"Error loading download directory: {e}")
            return os.path.expanduser('~/Downloads')

    def set_download_directory(self):
        """Open dialog to set download directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            self.download_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            try:
                self.download_dir = directory
                self.torrent_manager.set_save_path(directory)
                self.status_bar.showMessage(f"Download Directory: {directory}")
                logger.info(f"Download directory set to: {directory}")
            except Exception as e:
                logger.error(f"Error saving download directory: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save download directory: {str(e)}")

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
        
        pause_action = QAction("Pause", self)
        pause_action.triggered.connect(self.pause_selected_torrent)
        menu.addAction(pause_action)
        
        resume_action = QAction("Resume", self)
        resume_action.triggered.connect(self.resume_selected_torrent)
        menu.addAction(resume_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected_torrent)
        menu.addAction(delete_action)
        
        menu.exec(self.downloads_table.mapToGlobal(position)) 