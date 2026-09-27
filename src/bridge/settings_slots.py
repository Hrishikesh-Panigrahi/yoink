from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

import db
from utils import autostart, proxy, resolver
from utils.logger import setup_logger
from version import __version__
from workers import FreeProxyWorker

logger = setup_logger("bridge.settings")


class SettingsMixin:
    @pyqtSlot(result=str)
    def getSettings(self) -> str:
        return json.dumps(self._settings_dict())

    @pyqtSlot(str, bool)
    def setBoolSetting(self, key: str, value: bool) -> None:
        db.set_setting(key, "1" if value else "0")
        if key == "dns_over_https_enabled":
            # Applies without a restart. The cache is cleared so the next
            # lookup uses the new resolver.
            resolver.clear_cache()
            resolver.apply_from_settings()
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str, int)
    def setIntSetting(self, key: str, value: int) -> None:
        db.set_setting(key, str(int(value)))
        if key in {
            "download_limit_kb_s",
            "upload_limit_kb_s",
            "max_active_downloads",
            "max_active_seeds",
        }:
            self._apply_session_limits_from_db()
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str, float)
    def setFloatSetting(self, key: str, value: float) -> None:
        db.set_setting(key, f"{float(value):.4f}")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str)
    def setTmdbApiKey(self, key: str) -> None:
        cleaned = (key or "").strip()
        db.set_setting("tmdb_api_key", cleaned)
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(bool, result=bool)
    def setLaunchAtLogin(self, enabled: bool) -> bool:
        """Returns the state actually in effect, which can differ from `enabled`."""
        effective = autostart.set_enabled(enabled)
        self.settingsChanged.emit(json.dumps(self._settings_dict()))
        return effective

    @pyqtSlot(result=str)
    def exportSettings(self) -> str:
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Export Yoink settings",
                os.path.join(self.save_folder, "yoink-settings.json"),
                "JSON Files (*.json)",
            )
            if not file_path:
                return ""
            all_settings = db.get_all_settings()
            secrets = {"tmdb_api_key"}
            cleaned = {k: v for k, v in all_settings.items() if k not in secrets}
            payload = {
                "version": __version__,
                "exportedAt": __import__("time").time(),
                "settings": cleaned,
            }
            Path(file_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self.toast.emit("success", f"Exported settings to {os.path.basename(file_path)}")
            return file_path
        except Exception as exc:
            logger.exception("exportSettings failed")
            self.toast.emit("error", f"Export failed: {exc}")
            return ""

    @pyqtSlot(result=str)
    def importSettings(self) -> str:
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Import Yoink settings",
                self.save_folder,
                "JSON Files (*.json)",
            )
            if not file_path:
                return ""
            raw = Path(file_path).read_text(encoding="utf-8")
            payload = json.loads(raw)
            settings = payload.get("settings") if isinstance(payload, dict) else None
            if not isinstance(settings, dict):
                self.toast.emit("error", "Invalid settings file")
                return ""
            for key, value in settings.items():
                if not isinstance(key, str):
                    continue
                db.set_setting(key, str(value))
            self._apply_session_limits_from_db()
            self.settingsChanged.emit(json.dumps(self._settings_dict()))
            self.toast.emit("success", "Settings imported")
            return file_path
        except Exception as exc:
            logger.exception("importSettings failed")
            self.toast.emit("error", f"Import failed: {exc}")
            return ""

    @pyqtSlot(str, str, result=str)
    def setProxy(self, proxy_url: str, user_agent: str) -> str:
        """Save and apply the proxy. Returns an error message, or "" when it worked."""
        url = proxy.normalize(proxy_url)
        error = proxy.apply(url, user_agent)
        if error:
            return error
        db.set_setting("proxy_url", url)
        db.set_setting("user_agent", (user_agent or "").strip())
        self.settingsChanged.emit(json.dumps(self._settings_dict()))
        return ""

    @pyqtSlot()
    def findFreeProxy(self) -> None:
        """Test free proxies in the background. Progress arrives on `freeProxyProgress`;
        the one chosen is saved and applied, then reported on `freeProxyFound`."""
        if self._proxy_worker and self._proxy_worker.isRunning():
            return
        worker = FreeProxyWorker()
        worker.progress.connect(
            lambda tested, total, working: self.freeProxyProgress.emit(
                json.dumps({"tested": tested, "total": total, "working": working})
            )
        )
        worker.finished.connect(self._on_free_proxy)
        worker.start()
        self._proxy_worker = worker

    def _on_free_proxy(self, result) -> None:
        if result and self.setProxy(result["proxy"], db.get_setting("user_agent") or ""):
            result = None
        self.freeProxyFound.emit(json.dumps(result or {}))

    @pyqtSlot(result=str)
    def getProxy(self) -> str:
        return json.dumps({
            "proxyUrl": db.get_setting("proxy_url") or "",
            "userAgent": db.get_setting("user_agent") or "",
        })

    @pyqtSlot(result=str)
    def getSchedule(self) -> str:
        return json.dumps({
            "enabled": (db.get_setting("schedule_enabled") or "0") == "1",
            "quietStart": db.get_setting("schedule_quiet_start") or "00:00",
            "quietEnd": db.get_setting("schedule_quiet_end") or "08:00",
            "quietDownKbS": self._int_setting("schedule_quiet_down_kb_s", 0),
            "quietUpKbS": self._int_setting("schedule_quiet_up_kb_s", 0),
        })

    @pyqtSlot(str)
    def setSchedule(self, payload_json: str) -> None:
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        db.set_setting("schedule_enabled", "1" if payload.get("enabled") else "0")
        db.set_setting("schedule_quiet_start", str(payload.get("quietStart") or "00:00"))
        db.set_setting("schedule_quiet_end", str(payload.get("quietEnd") or "08:00"))
        db.set_setting("schedule_quiet_down_kb_s", str(int(payload.get("quietDownKbS") or 0)))
        db.set_setting("schedule_quiet_up_kb_s", str(int(payload.get("quietUpKbS") or 0)))
        # Makes the worker reapply the limits on its next tick.
        self.schedule_worker._last_window = ""
