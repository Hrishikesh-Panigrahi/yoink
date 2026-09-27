from __future__ import annotations

import os
import sys
import traceback

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from utils.logger import setup_logger
from utils.paths import default_log_path
from utils.single_instance import send_to_existing

LOG_FILE = default_log_path()
logger = setup_logger("yoink", LOG_FILE)


def _log_unhandled(exc_type, exc_value, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical(
        "Unhandled exception:\n"
        + "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip()
    )


def _install_exception_logger() -> None:
    """Log an exception that escapes a slot, and keep the app running.

    Exceptions inside `app.exec()` (slots, timers, signal handlers) never reach
    the `try` in `__main__`. PyQt passes them to `sys.excepthook`, and while
    that is still the default hook it aborts the process with nothing logged.
    """
    sys.excepthook = _log_unhandled


def _extract_payload(argv: list[str]) -> str:
    """The first magnet link or .torrent path on the command line, or ''."""
    for arg in argv[1:]:
        if arg.startswith("magnet:") or arg.lower().endswith(".torrent"):
            return arg
    return ""


def _apply_network_settings() -> None:
    """DNS over HTTPS unless the user turned it off, and the saved proxy if there is one."""
    try:
        import db
        from utils import proxy, resolver

        db.init_db()
        resolver.apply_from_settings()
        error = proxy.apply_from_settings()
        if error:
            logger.warning(f"Saved proxy not used: {error}")
    except Exception as exc:
        # Not worth blocking startup for. Searches still work without them.
        logger.warning(f"Could not apply the network settings: {exc}")


def main() -> None:
    logger.info("Starting Yoink")
    _install_exception_logger()

    payload = _extract_payload(sys.argv)
    if payload and send_to_existing(payload):
        logger.info("Handed CLI payload off to existing Yoink instance; exiting")
        return

    # Must run before MainWindow: it builds the Bridge, whose workers go
    # online right away.
    _apply_network_settings()

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
