from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QLabel, QProgressBar, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from core.torrent_manager import TorrentManager
from database.database import DatabaseManager
from utils.search import SearchUtil
from .loading_dialog import LoadingDialog
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        self.torrent_manager = TorrentManager()
        self.db_manager = DatabaseManager()
        self.search_util = SearchUtil()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for torrents...")
        self.search_input.returnPressed.connect(self.search_torrents)
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_torrents)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        
        # Create torrent list table
        self.torrent_table = QTableWidget()
        self.torrent_table.setColumnCount(5)
        self.torrent_table.setHorizontalHeaderLabels([
            "Name", "Size", "Progress", "Speed", "Status"
        ])
        self.torrent_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.torrent_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.torrent_table)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        # Set up timer for updating torrent list
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_torrent_list)
        self.update_timer.start(1000)  # Update every second
        
        # Initial torrent list update
        self.update_torrent_list()
        
    def search_torrents(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search term")
            return
            
        # Show loading dialog
        loading_dialog = LoadingDialog(self, "Searching for torrents...")
        loading_dialog.show()
        QApplication.processEvents()
        
        try:
            results = self.search_util.search_torrents(query)
            loading_dialog.close()
            
            if not results:
                QMessageBox.information(self, "No Results", 
                    "No torrents found. Try a different search term.")
                return
                
            self.show_search_results(results)
            
        except Exception as e:
            loading_dialog.close()
            QMessageBox.critical(self, "Error", 
                f"An error occurred while searching: {str(e)}\nPlease try again later.")
            logging.error(f"Search error: {str(e)}")
        
    def show_search_results(self, results):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Search Results")
        dialog.setMinimumWidth(800)
        
        # Create a table widget for results
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Name", "Size", "Seeds", "Peers", "Source", "Quality"
        ])
        
        table.setRowCount(len(results))
        for i, result in enumerate(results):
            # Store magnet link as user data
            name_item = QTableWidgetItem(result.name)
            name_item.setData(Qt.ItemDataRole.UserRole, result.magnet_link)
            table.setItem(i, 0, name_item)
            
            table.setItem(i, 1, QTableWidgetItem(self.search_util.format_size(result.size)))
            table.setItem(i, 2, QTableWidgetItem(str(result.seeds)))
            table.setItem(i, 3, QTableWidgetItem(str(result.peers)))
            table.setItem(i, 4, QTableWidgetItem(result.source))
            
            # Extract quality from name if available
            quality = "N/A"
            if "1080p" in result.name:
                quality = "1080p"
            elif "720p" in result.name:
                quality = "720p"
            elif "4K" in result.name or "2160p" in result.name:
                quality = "4K"
            table.setItem(i, 5, QTableWidgetItem(quality))
            
        # Adjust column widths
        table.resizeColumnsToContents()
        
        # Add download button
        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(lambda: self.download_selected(table))
        
        # Create layout
        layout = QVBoxLayout()
        layout.addWidget(table)
        layout.addWidget(download_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
        
    def download_selected(self, table):
        selected_items = table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a torrent to download")
            return
            
        row = selected_items[0].row()
        magnet_link = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if magnet_link:
            try:
                self.torrent_manager.add_torrent(magnet_link)
                self.update_torrent_list()
                self.statusBar().showMessage("Torrent added successfully", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add torrent: {str(e)}")
            
    def update_torrent_list(self):
        torrents = self.torrent_manager.get_all_torrents()
        self.torrent_table.setRowCount(len(torrents))
        
        for i, torrent in enumerate(torrents):
            self.torrent_table.setItem(i, 0, QTableWidgetItem(torrent.name))
            self.torrent_table.setItem(i, 1, QTableWidgetItem(self.search_util.format_size(torrent.size)))
            
            progress = QProgressBar()
            progress.setValue(int(torrent.progress))
            self.torrent_table.setCellWidget(i, 2, progress)
            
            self.torrent_table.setItem(i, 3, QTableWidgetItem(
                f"↓ {self.search_util.format_size(torrent.download_rate)}/s"
            ))
            self.torrent_table.setItem(i, 4, QTableWidgetItem(torrent.state))
            
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