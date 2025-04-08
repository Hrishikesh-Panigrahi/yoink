from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath
import math

class LoadingDialog(QDialog):
    def __init__(self, parent=None, message="Searching for torrents..."):
        super().__init__(parent)
        self.setWindowTitle("Searching")
        self.setFixedSize(300, 150)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Message label
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        
        # Add widgets to layout
        layout.addWidget(self.message_label)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        # Animation timer
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)  # Update every 50ms
        
    def rotate(self):
        self.angle = (self.angle + 5) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background with rounded corners
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)
        
        # Set background color with slight transparency
        painter.fillPath(path, QColor(255, 255, 255, 240))
        
        # Draw border
        painter.setPen(QColor(200, 200, 200))
        painter.drawPath(path)
        
    def update_message(self, message):
        self.message_label.setText(message) 