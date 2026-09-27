"""Find a libvlc runtime and import `vlc` safely.

`python-vlc` is only a ctypes binding. Importing it searches for `libvlc.dll` and
raises `FileNotFoundError` if it finds nothing, so `import vlc` must never sit at
the top of a module in this app. Go through `load_vlc()`, which returns an error
message instead of raising and caches the result.

Search order, first hit wins: `YOINK_VLC_DIR`, the copy bundled with a frozen
build, a portable copy in Yoink's data folder, then an installed VLC (Windows
only: registry, then the usual install directories). On other platforms, if
nothing is found, the plain import is tried and the system loader finds libvlc.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from utils.logger import setup_logger
from utils.paths import app_data_dir

logger = setup_logger("player.runtime")

#: Points at a directory holding libvlc.dll and a plugins/ folder.
DIR_ENV_VAR = "YOINK_VLC_DIR"

BUNDLED_SUBDIR = "vlc"

#: A portable VLC placed here is found with no setup. This helps when the user
#: cannot run the VLC installer, which needs admin rights.
DATA_DIR_SUBDIR = "vlc"

_WINDOWS_INSTALL_DIRS = (
    r"C:\Program Files\VideoLAN\VLC",
    r"C:\Program Files (x86)\VideoLAN\VLC",
)

_REGISTRY_KEYS = (
    r"SOFTWARE\VideoLAN\VLC",
    r"SOFTWARE\WOW6432Node\VideoLAN\VLC",
)


@dataclass(frozen=True)
class Runtime:
    """A directory holding a usable libvlc and its plugins."""

    directory: Path
    library: Path
    plugin_path: Path
    source: str  # how it was found, shown in logs and the About panel


def _is_windows() -> bool:
    return sys.platform == "win32"


def _library_name() -> str:
    return "libvlc.dll" if _is_windows() else "libvlc.so"


def _looks_like_a_runtime(directory: Path) -> Optional[Runtime]:
    if not directory or not directory.is_dir():
        return None
    library = directory / _library_name()
    plugins = directory / "plugins"
    if not library.exists() or not plugins.is_dir():
        return None
    return Runtime(directory=directory, library=library, plugin_path=plugins, source="")


def _bundled_dir() -> Optional[Path]:
    """Where a PyInstaller build unpacks its bundled runtime."""
    if not getattr(sys, "frozen", False):
        return None
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    return Path(base) / BUNDLED_SUBDIR


def _data_dir() -> Optional[Path]:
    try:
        return Path(app_data_dir(create=False)) / DATA_DIR_SUBDIR
    except Exception as exc:
        logger.debug(f"Could not resolve the data directory: {exc}")
        return None


def _registry_dirs() -> List[Path]:
    if not _is_windows():
        return []
    try:
        import winreg
    except ImportError:  # pragma: no cover
        return []
    found: List[Path] = []
    for key_path in _REGISTRY_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "InstallDir")
        except OSError:
            continue
        if value:
            found.append(Path(value))
    return found


def find_runtime() -> Optional[Runtime]:
    candidates: List[Tuple[str, Path]] = []

    override = os.environ.get(DIR_ENV_VAR, "").strip()
    if override:
        candidates.append((DIR_ENV_VAR, Path(override)))

    bundled = _bundled_dir()
    if bundled:
        candidates.append(("bundled", bundled))

    data_dir = _data_dir()
    if data_dir:
        candidates.append(("data dir", data_dir))

    for directory in _registry_dirs():
        candidates.append(("registry", directory))
    for raw in _WINDOWS_INSTALL_DIRS if _is_windows() else ():
        candidates.append(("install dir", Path(raw)))

    for source, directory in candidates:
        runtime = _looks_like_a_runtime(directory)
        if runtime is not None:
            return Runtime(runtime.directory, runtime.library, runtime.plugin_path, source)
    return None


# The import is slow and its outcome does not change during a run.
_cache: Optional[Tuple[Optional[object], str]] = None


def load_vlc(force: bool = False) -> Tuple[Optional[object], str]:
    """Import `vlc` with a runtime prepared. Returns `(module, error)`.

    On success `error` is empty. On failure `module` is None and `error` says
    what the user can do about it.
    """
    global _cache
    if _cache is not None and not force:
        return _cache
    _cache = _load_vlc_uncached()
    return _cache


def _load_vlc_uncached() -> Tuple[Optional[object], str]:
    runtime = find_runtime()
    if runtime is None and _is_windows():
        return None, (
            "VLC was not found. Install VLC, or set "
            f"{DIR_ENV_VAR} to a folder containing libvlc.dll and plugins/."
        )

    if runtime is not None:
        # python-vlc's loader reads these two. Without them it does its own
        # search and falls back to `CDLL(".\\libvlc.dll")`, a relative path that
        # resolves against the working directory and fails. add_dll_directory
        # and VLC_PLUGIN_PATH do not change that.
        os.environ["PYTHON_VLC_LIB_PATH"] = str(runtime.library)
        os.environ["PYTHON_VLC_MODULE_PATH"] = str(runtime.plugin_path)
        # libvlc reads this one after it loads.
        os.environ["VLC_PLUGIN_PATH"] = str(runtime.plugin_path)
        if _is_windows():
            # Lets libvlc.dll find libvlccore.dll next to it.
            try:
                os.add_dll_directory(str(runtime.directory))
            except (OSError, AttributeError) as exc:
                logger.warning(f"add_dll_directory failed for {runtime.directory}: {exc}")
        logger.info(f"Using libvlc from {runtime.directory} (found via {runtime.source})")

    try:
        import vlc
    except SystemExit as exc:
        # python-vlc calls sys.exit(1) when the library or plugin path will not
        # load. SystemExit is not an Exception, so without this the app would exit.
        return None, f"VLC refused to load from {runtime.library if runtime else '?'} ({exc})"
    except Exception as exc:
        return None, f"Could not load VLC: {exc}"

    return vlc, ""


def is_available() -> bool:
    module, _ = load_vlc()
    return module is not None


def describe() -> dict:
    """Player runtime details for the UI, including why it is unavailable."""
    module, error = load_vlc()
    runtime = find_runtime()
    version = ""
    if module is not None:
        try:
            raw = module.libvlc_get_version()
            version = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        except Exception as exc:
            logger.debug(f"libvlc_get_version failed: {exc}")
    return {
        "available": module is not None,
        "reason": error,
        "version": version,
        "directory": str(runtime.directory) if runtime else "",
        "source": runtime.source if runtime else "",
    }


def reset_cache() -> None:
    """Forget the cached import. Used by tests."""
    global _cache
    _cache = None
