"""Launch at login through the HKCU Run registry key. On other platforms these do nothing."""

from __future__ import annotations

import os
import sys

from utils.logger import setup_logger

logger = setup_logger("utils.autostart")

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Yoink"


def _launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --minimized'


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """Turn launch at login on or off. Returns the state read back from the registry."""
    if sys.platform != "win32":
        logger.warning("Autostart toggle requested on non-Windows; ignoring")
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
        return is_enabled()
    except OSError as exc:
        logger.error(f"Autostart toggle failed: {exc}")
        return is_enabled()
