import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow
from utils.logger import setup_logger

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
log_file = os.path.join(log_dir, 'torrent_app.log')
logger = setup_logger('torrent_app', log_file)

def main():
    logger.info("Starting Torrent App")
    
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    logger.debug("Application style set to Fusion")
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'app_icon.png')
    app.setWindowIcon(QIcon(icon_path))
    logger.debug(f"Application icon set from {icon_path}")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    logger.info("Main window created and shown")
    
    # Start the application event loop
    logger.info("Starting application event loop")
    sys.exit(app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 