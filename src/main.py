"""Yoink entrypoint."""

from __future__ import annotations

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from utils.logger import setup_logger

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "yoink.log")
logger = setup_logger("yoink", LOG_FILE)


def main() -> None:
    logger.info("Starting Yoink")

    app = QApplication(sys.argv)
    app.setApplicationName("Yoink")
    app.setOrganizationName("Yoink")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    icon_path = os.path.join(os.path.dirname(__file__), "resources", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.critical(f"Unhandled exception: {exc}", exc_info=True)
        sys.exit(1)
