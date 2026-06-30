"""Settings persistence: get/set, export/import, proxy, schedule."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

import db
from utils import autostart
from utils.logger import setup_logger
from version import __version__

logger = setup_logger("bridge.settings")


class SettingsMixin:
    """Mixin providing settings/preferences QWebChannel slots."""

    @pyqtSlot(result=str)
    def getSettings(self) -> str:
        """Return the current persisted settings as JSON."""
        return json.dumps(self._settings_dict())

    @pyqtSlot(str, bool)
    def setBoolSetting(self, key: str, value: bool) -> None:
        """Persist a boolean setting and notify listeners."""
        db.set_setting(key, "1" if value else "0")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str, int)
    def setIntSetting(self, key: str, value: int) -> None:
        """Persist an int setting (bandwidth caps, active limits)."""
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
        """Persist a float setting (e.g. seed_ratio_limit)."""
        db.set_setting(key, f"{float(value):.4f}")
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(str)
    def setTmdbApiKey(self, key: str) -> None:
        """Persist the user's TMDB API key (empty string clears it)."""
        cleaned = (key or "").strip()
        db.set_setting("tmdb_api_key", cleaned)
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

    @pyqtSlot(bool, result=bool)
    def setLaunchAtLogin(self, enabled: bool) -> bool:
        """Toggle Windows launch-at-login. Returns the effective state."""
        effective = autostart.set_enabled(enabled)
        self.settingsChanged.emit(json.dumps(self._settings_dict()))
        return effective

    @pyqtSlot(result=str)
    def exportSettings(self) -> str:
        """Write all settings to a user-picked JSON file. Returns the path or ''."""
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
        """Pick a JSON file and replace current settings. Returns the path or ''."""
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

    @pyqtSlot(str, str)
    def setProxy(self, proxy_url: str, user_agent: str) -> None:
        """Persist proxy + UA. Applied to providers' shared requests session."""
        db.set_setting("proxy_url", (proxy_url or "").strip())
        db.set_setting("user_agent", (user_agent or "").strip())
        try:
            from providers import _http  # provider http session module if present
            _http.apply_proxy_and_ua()
        except Exception:
            pass
        self.settingsChanged.emit(json.dumps(self._settings_dict()))

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
        # Reset cached state so the worker reapplies on next tick.
        self.schedule_worker._last_window = ""
