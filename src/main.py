"""Yoink entrypoint."""

from __future__ import annotations

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from utils.logger import setup_logger
from utils.paths import default_log_path
from utils.single_instance import send_to_existing

LOG_FILE = default_log_path()
logger = setup_logger("yoink", LOG_FILE)


def _extract_payload(argv: list[str]) -> str:
    """Return a magnet link or .torrent path passed via CLI, if any."""
    for arg in argv[1:]:
        if arg.startswith("magnet:") or arg.lower().endswith(".torrent"):
            return arg
    return ""


def _apply_dns_setting() -> None:
    """Switch name resolution to DoH unless the user turned it off."""
    try:
        import db
        from utils import resolver

        db.init_db()
        resolver.apply_from_settings()
    except Exception as exc:
        # Never block startup over this - the system resolver still works.
        logger.warning(f"Could not apply the DNS setting: {exc}")


def main() -> None:
    logger.info("Starting Yoink")

    payload = _extract_payload(sys.argv)
    if payload and send_to_existing(payload):
        logger.info("Handed CLI payload off to existing Yoink instance; exiting")
        return

    # Before the window, because MainWindow builds the Bridge, which starts
    # workers that reach the network immediately.
    _apply_dns_setting()

    app = QApplication(sys.argv)
    app.setApplicationName("Yoink")
    app.setOrganizationName("Yoink")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    icon_path = os.path.join(os.path.dirname(__file__), "resources", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow(initial_payload=payload)
    if "--minimized" in sys.argv[1:]:
        logger.info("Launched with --minimized; keeping window hidden")
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.critical(f"Unhandled exception: {exc}", exc_info=True)
        sys.exit(1)
