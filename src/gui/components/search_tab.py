"""Search tab component for the main window."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional

from utils.search import SearchResult
from utils.logger import setup_logger
from .workers import SearchWorker

logger = setup_logger('search_tab')

class SearchTab(QWidget):
    """Search tab widget."""
    
    # Signals
    torrent_selected = pyqtSignal(SearchResult)
    
    def __init__(self, search_util, parent=None):
        super().__init__(parent)
        self.search_util = search_util
        self.current_page = 1
        self.total_pages = 1
        self.total_results = 0
        self.search_worker: Optional[SearchWorker] = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search torrents...")
        self.search_input.returnPressed.connect(self.search_torrents)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_torrents)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Name", "Size", "Seeds", "Peers", "Added"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.doubleClicked.connect(self.on_result_double_clicked)
        layout.addWidget(self.results_table)
        
        # Pagination
        pagination_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.previous_page)
        self.prev_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = QLabel("Page 1 of 1")
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        pagination_layout.addWidget(self.next_button)
        
        layout.addLayout(pagination_layout)
        
        # Status bar
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def search_torrents(self):
        """Search for torrents."""
        query = self.search_input.text().strip()
        if not query:
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("Searching...")
        
        # Start search worker
        if self.search_worker is not None:
            self.search_worker.quit()
            self.search_worker.wait()
        
        self.search_worker = SearchWorker(self.search_util, query, self.current_page)
        self.search_worker.finished.connect(self.on_search_completed)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()
    
    def on_search_completed(self, results: List[SearchResult], total_results: int, total_pages: int):
        """Handle search completion."""
        self.total_results = total_results
        self.total_pages = total_pages
        
        # Update UI
        self.show_search_results(results)
        self.update_pagination_controls()
        self.update_status()
        
        # Hide progress
        self.progress_bar.setVisible(False)
    
    def on_search_error(self, error_msg: str):
        """Handle search error."""
        self.status_label.setText(f"Error: {error_msg}")
        self.progress_bar.setVisible(False)
    
    def show_search_results(self, results: List[SearchResult]):
        """Display search results in the table."""
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # Name
            name_item = QTableWidgetItem(result.name)
            name_item.setData(Qt.ItemDataRole.UserRole, result)
            self.results_table.setItem(row, 0, name_item)
            
            # Size
            size_item = QTableWidgetItem(self.format_size(result.size))
            self.results_table.setItem(row, 1, size_item)
            
            # Seeds
            seeds_item = QTableWidgetItem(str(result.seeds))
            self.results_table.setItem(row, 2, seeds_item)
            
            # Peers
            peers_item = QTableWidgetItem(str(result.peers))
            self.results_table.setItem(row, 3, peers_item)
            
            # Added
            added_item = QTableWidgetItem(result.added.strftime("%Y-%m-%d"))
            self.results_table.setItem(row, 4, added_item)
    
    def update_pagination_controls(self):
        """Update pagination controls state."""
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
    
    def update_status(self):
        """Update status label."""
        self.status_label.setText(
            f"Found {self.total_results} results "
            f"(Page {self.current_page} of {self.total_pages})"
        )
    
    def previous_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.search_torrents()
    
    def next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.search_torrents()
    
    def on_result_double_clicked(self, index):
        """Handle double click on a search result."""
        item = self.results_table.item(index.row(), 0)
        if item:
            result = item.data(Qt.ItemDataRole.UserRole)
            self.torrent_selected.emit(result)
    
    @staticmethod
    def format_size(bytes: int) -> str:
        """Format size in bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB" 