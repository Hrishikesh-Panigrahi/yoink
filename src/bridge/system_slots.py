from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import webbrowser

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

import db
import torrents
from utils.logger import setup_logger
from utils.paths import app_data_dir
from version import __app_homepage__, __version__

logger = setup_logger("bridge.system")


class SystemMixin:
    @pyqtSlot(result=str)
    def getSaveFolder(self) -> str:
        return self.save_folder

    @pyqtSlot(result=str)
    def pickSaveFolder(self) -> str:
        try:
            new_dir = QFileDialog.getExistingDirectory(
                None,
                "Select Download Folder",
                self.save_folder,
                QFileDialog.Option.ShowDirsOnly,
            )
            if not new_dir:
                return self.save_folder
            self.save_folder = new_dir
            torrents.set_save_path(self.session, new_dir)
            db.set_setting("download_directory", new_dir)
            self.saveFolderChanged.emit(new_dir)
            self.toast.emit("success", f"Save folder set to {new_dir}")
            return new_dir
        except Exception as exc:
            logger.exception("pickSaveFolder failed")
            self.toast.emit("error", str(exc))
            return self.save_folder

    @pyqtSlot(str)
    def openSaveFolder(self, path: str = "") -> None:
        target = path or self.save_folder
        try:
            os.startfile(target)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.error(f"openSaveFolder failed: {exc}")
            self.toast.emit("error", f"Cannot open folder: {exc}")

    @pyqtSlot()
    def openDataFolder(self) -> None:
        try:
            os.startfile(app_data_dir())  # type: ignore[attr-defined]
        except Exception as exc:
            logger.error(f"openDataFolder failed: {exc}")
            self.toast.emit("error", f"Cannot open data folder: {exc}")

    @pyqtSlot(str)
    def openPath(self, path: str) -> None:
        target = (path or "").strip()
        if not target:
            return
        try:
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as exc:
            logger.error(f"openPath failed: {exc}")
            self.toast.emit("error", f"Cannot open: {exc}")

    @pyqtSlot(str)
    def revealInExplorer(self, path: str) -> None:
        target = (path or "").strip()
        if not target:
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", target])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", target])
            else:
                folder = target if os.path.isdir(target) else os.path.dirname(target)
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            logger.error(f"revealInExplorer failed: {exc}")
            self.toast.emit("error", f"Cannot reveal: {exc}")

    @pyqtSlot(str)
    def openExternal(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception as exc:
            logger.error(f"openExternal failed: {exc}")
            self.toast.emit("error", f"Cannot open link: {exc}")

    @pyqtSlot(result=str)
    def pickWatchFolder(self) -> str:
        folder = QFileDialog.getExistingDirectory(
            None,
            "Pick watch folder",
            db.get_setting("watch_folder") or self.save_folder,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return db.get_setting("watch_folder") or ""
        db.set_setting("watch_folder", folder)
        self.watch_worker.update_folder(folder)
        if not self.watch_worker.isRunning():
            self.watch_worker.start()
        self.settingsChanged.emit(json.dumps(self._settings_dict()))
        self.toast.emit("success", f"Watching {folder}")
        return folder

    @pyqtSlot()
    def clearWatchFolder(self) -> None:
        db.set_setting("watch_folder", "")
        self.watch_worker.update_folder("")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(result=str)
    def getAboutInfo(self) -> str:
        return json.dumps({
            "version": __version__,
            "homepage": __app_homepage__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        })

    @pyqtSlot(str, str, str)
    def notify(self, kind: str, title: str, message: str) -> None:
        if not self._notifications_enabled():
            return
        self.requestNotification.emit(title or "Yoink", message or "")

    @pyqtSlot(result=str)
    def listCommands(self) -> str:
        """Entries for the JS command palette. Each `id` is run by `runCommand`."""
        commands = [
            {"id": "pauseAll", "label": "Pause all torrents"},
            {"id": "resumeAll", "label": "Resume all torrents"},
            {"id": "openSaveFolder", "label": "Open downloads folder"},
            {"id": "openDataFolder", "label": "Open data folder (logs / db)"},
            {"id": "pickSaveFolder", "label": "Change downloads folder..."},
            {"id": "refreshProviderHealth", "label": "Refresh provider health"},
        ]
        return json.dumps(commands)

    @pyqtSlot(str)
    def runCommand(self, command_id: str) -> None:
        handlers = {
            "pauseAll": lambda: self.pauseAll(),
            "resumeAll": lambda: self.resumeAll(),
            "openSaveFolder": lambda: self.openSaveFolder(""),
            "openDataFolder": lambda: self.openDataFolder(),
            "pickSaveFolder": lambda: self.pickSaveFolder(),
            "refreshProviderHealth": lambda: self.refreshProviderHealth(),
        }
        handler = handlers.get(command_id)
        if handler is None:
            return
        try:
            handler()
        except Exception as exc:
            logger.error(f"runCommand({command_id}) failed: {exc}")
