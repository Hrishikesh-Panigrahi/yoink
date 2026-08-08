"""QMainWindow that hosts the QWebEngineView, tray icon, and bridge."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QEvent, QUrl
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon

import db
from bridge import Bridge
from utils.logger import setup_logger
from utils.single_instance import listen as listen_for_handoff

logger = setup_logger("main_window")


def _web_root() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        candidate = base / "web"
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent / "web"


def _resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        return base / "resources" / Path(*parts)
    return Path(__file__).resolve().parent / "resources" / Path(*parts)


class MainWindow(QMainWindow):
    """Top-level window: web view + tray icon + bridge."""

    def __init__(self, initial_payload: str = ""):
        super().__init__()
        logger.info("Initializing MainWindow")
        self._initial_payload = (initial_payload or "").strip()
        self._handoff_server = listen_for_handoff(self._handle_handoff_payload)

        self.setWindowTitle("Yoink")
        self.setMinimumSize(1080, 720)
        self.resize(1280, 820)

        icon_path = _resource_path("app_icon.png")
        self.app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        self.bridge = Bridge(self)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.bridge.requestNotification.connect(self._show_notification)

        self._force_quit = False
        self.tray = self._build_tray()
        self._last_clipboard_magnet = ""

        self.bridge.downloadsUpdated.connect(self._update_tray_tooltip)

        index_url = QUrl.fromLocalFile(str(_web_root() / "index.html"))
        logger.info(f"Loading UI from {index_url.toString()}")
        self.view.load(index_url)
        if self._initial_payload:
            self.view.loadFinished.connect(self._consume_initial_payload)

    def _consume_initial_payload(self, ok: bool) -> None:
        if not ok or not self._initial_payload:
            return
        self._handle_handoff_payload(self._initial_payload)
        self._initial_payload = ""

    def _handle_handoff_payload(self, payload: str) -> None:
        """Add a magnet/.torrent passed via CLI handoff and surface the window."""
        payload = (payload or "").strip()
        if not payload:
            return
        try:
            if payload.startswith("magnet:"):
                self.bridge.addTorrent(payload)
            else:
                if os.path.isfile(payload):
                    import torrents
                    torrents.set_save_path(self.bridge.session, self.bridge.save_folder)
                    torrents.add_torrent_file(self.bridge.session, payload)
                    self.bridge.toast.emit("success", f"Added: {os.path.basename(payload)}")
        except Exception as exc:
            logger.error(f"Handoff payload failed: {exc}")
            self.bridge.toast.emit("error", str(exc))
        self._show_from_tray()

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self.app_icon, self)
        tray.setToolTip("Yoink")
        menu = QMenu(self)

        show_action = QAction("Show Yoink", self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)
        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_from_tray)
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        return tray

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._force_quit = True
        self.close()

    def _update_tray_tooltip(self, payload_json: str) -> None:
        """Tray progress (9.1): reflect active count + speeds in the tooltip."""
        try:
            items = json.loads(payload_json or "[]")
        except Exception:
            return
        active = [
            t
            for t in items
            if (t.get("progress") or 0) < 100
            and "error" not in (t.get("status") or "").lower()
        ]
        if not active:
            self.tray.setToolTip("Yoink — idle")
            return
        names = ", ".join((t.get("name") or "?")[:32] for t in active[:2])
        tail = "" if len(active) <= 2 else f" and {len(active) - 2} more"
        self.tray.setToolTip(f"Yoink — {len(active)} downloading\n{names}{tail}")

    def changeEvent(self, event):
        """Clipboard magnet watcher (2.2): peek when the window gains focus."""
        try:
            if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
                self._maybe_emit_clipboard_magnet()
        except Exception:
            pass
        super().changeEvent(event)

    def _maybe_emit_clipboard_magnet(self) -> None:
        if (db.get_setting("clipboard_watcher_enabled") or "0") != "1":
            return
        try:
            text = (QApplication.clipboard().text() or "").strip()
        except Exception:
            return
        if not text or not text.startswith("magnet:?xt=urn:btih:"):
            return
        if text == self._last_clipboard_magnet:
            return
        self._last_clipboard_magnet = text
        self.bridge.clipboardMagnet.emit(text)

    def _show_notification(self, title: str, body: str) -> None:
        try:
            if self.tray and self.tray.isVisible():
                self.tray.showMessage(
                    title or "Yoink",
                    body or "",
                    self.app_icon
                    if not self.app_icon.isNull()
                    else QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
        except Exception as exc:
            logger.error(f"Notification failed: {exc}")

    def closeEvent(self, event):
        if (
            not self._force_quit
            and self.tray is not None
            and self.tray.isVisible()
            and self.bridge.minimize_to_tray_enabled()
        ):
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Yoink",
                "Still running in the tray. Right-click the tray icon to quit.",
                self.app_icon
                if not self.app_icon.isNull()
                else QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
            return

        logger.info("MainWindow closing - shutting down bridge")
        try:
            self.bridge.shutdown()
        except Exception as exc:
            logger.error(f"Bridge shutdown error: {exc}")
        if self.tray is not None:
            self.tray.hide()
        QApplication.instance().quit()
        super().closeEvent(event)
