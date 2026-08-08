"""Finding a libvlc runtime and importing `vlc` without blowing up.

`python-vlc` is a ctypes binding, not a copy of VLC. Importing it runs a search
for `libvlc.dll` at *import* time and raises `FileNotFoundError` when it comes up
empty — so `import vlc` can never sit at the top of a module in this app. Every
entry point here goes through `load_vlc()`, which returns a reason instead of
raising and caches the outcome.

Search order, first hit wins:

1. `YOINK_VLC_DIR`, for anyone pointing at a portable copy.
2. The runtime bundled beside a frozen build (`_MEIPASS/vlc`).
3. An installed VLC, via the registry then the usual install directories.

On anything other than Windows the system loader already knows where libvlc
lives, so discovery is skipped and the plain import is used.
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

#: Set this to a directory holding libvlc.dll and a plugins/ folder.
DIR_ENV_VAR = "YOINK_VLC_DIR"

#: Where a frozen build keeps its bundled copy, relative to the unpack dir.
BUNDLED_SUBDIR = "vlc"

#: A portable VLC dropped in here is picked up with no configuration. Useful
#: when installing VLC properly is not an option — the system installer needs
#: administrator rights, this does not.
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
    """A directory that actually holds a usable libvlc."""

    directory: Path
    library: Path
    plugin_path: Path
    source: str  # how it was found, for logs and the About panel


def _is_windows() -> bool:
    return sys.platform == "win32"


def _library_name() -> str:
    return "libvlc.dll" if _is_windows() else "libvlc.so"


def _looks_like_a_runtime(directory: Path) -> Optional[Runtime]:
    """A runtime needs the library itself and its plugin tree beside it."""
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
    """Yoink's own data folder, where a portable VLC can be dropped."""
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
    except ImportError:  # pragma: no cover - Windows only
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
    """Return the first directory that holds a usable libvlc, or None."""
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


# `load_vlc` is called from several places per session; the import is the
# expensive part and its failure mode is stable, so the outcome is cached.
_cache: Optional[Tuple[Optional[object], str]] = None


def load_vlc(force: bool = False) -> Tuple[Optional[object], str]:
    """Import `vlc` with a runtime prepared. Returns `(module, error)`.

    Exactly one of the two is set: on success `error` is empty, on failure
    `module` is None and `error` says what a user could do about it.
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
        # These two are the ones python-vlc's own loader reads. Without them it
        # runs its own registry / Program Files search and then falls back to
        # `CDLL(".\\libvlc.dll")` — a *relative* path, so it resolves against the
        # working directory and finds nothing. Neither add_dll_directory nor
        # VLC_PLUGIN_PATH influences that decision.
        os.environ["PYTHON_VLC_LIB_PATH"] = str(runtime.library)
        os.environ["PYTHON_VLC_MODULE_PATH"] = str(runtime.plugin_path)
        # libvlc itself reads this one once it is loaded.
        os.environ["VLC_PLUGIN_PATH"] = str(runtime.plugin_path)
        if _is_windows():
            # So libvlc.dll can resolve libvlccore.dll sitting beside it.
            try:
                os.add_dll_directory(str(runtime.directory))
            except (OSError, AttributeError) as exc:
                logger.warning(f"add_dll_directory failed for {runtime.directory}: {exc}")
        logger.info(f"Using libvlc from {runtime.directory} (found via {runtime.source})")

    try:
        import vlc  # noqa: PLC0415 — deliberately late; see the module docstring
    except SystemExit as exc:
        # python-vlc calls sys.exit(1) rather than raising when the library or
        # plugin path it was handed will not load. That is a BaseException, so
        # without this it would sail past `except Exception` and kill the app.
        return None, f"VLC refused to load from {runtime.library if runtime else '?'} ({exc})"
    except Exception as exc:
        return None, f"Could not load VLC: {exc}"

    return vlc, ""


def is_available() -> bool:
    module, _ = load_vlc()
    return module is not None


def describe() -> dict:
    """Player-runtime facts for the UI: is it usable, and if not, why not."""
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
    """Forget the cached import. Only useful in tests."""
    global _cache
    _cache = None
