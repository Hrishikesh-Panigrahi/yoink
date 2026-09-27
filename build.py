#!/usr/bin/env python3
"""Build Yoink for Windows: `dist/Yoink.exe`, then the installer if Inno Setup is found.

Usage:
    python build.py             # exe and installer
    python build.py --exe-only  # skip the installer
    python build.py --help      # other options
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

#: Folder for the VLC runtime inside the bundle. Must match `player.runtime.BUNDLED_SUBDIR`.
VLC_BUNDLE_DIR = "vlc"

#: Checked in order. YOINK_VLC_DIR can point at a portable VLC copy.
VLC_SEARCH_DIRS = (
    os.environ.get("YOINK_VLC_DIR", ""),
    r"C:\Program Files\VideoLAN\VLC",
    r"C:\Program Files (x86)\VideoLAN\VLC",
)


def find_vlc_runtime() -> Path | None:
    for raw in VLC_SEARCH_DIRS:
        if not raw:
            continue
        directory = Path(raw)
        if (directory / "libvlc.dll").exists() and (directory / "plugins").is_dir():
            return directory
    return None


def vlc_bundle_args(sep: str, required: bool) -> list[str]:
    """PyInstaller flags that copy the VLC runtime into the bundle.

    The whole plugins/ tree goes in, because libvlc can't decode anything without it.
    """
    runtime = find_vlc_runtime()
    if runtime is None:
        message = (
            "VLC runtime not found. The in-app player will not work in this build.\n"
            "  Install VLC (https://www.videolan.org/vlc/) or set YOINK_VLC_DIR to a\n"
            "  folder containing libvlc.dll and plugins/."
        )
        if required:
            raise SystemExit(f"build: {message}\n  Pass --no-player to build without it.")
        # Keep this ASCII. Piped output on Windows uses cp1252, where a non-ASCII
        # print raises UnicodeEncodeError.
        print(f"build: WARNING - {message}")
        return []

    print(f"build: bundling VLC runtime from {runtime}")
    args = [
        f"--add-binary={runtime / 'libvlc.dll'}{sep}{VLC_BUNDLE_DIR}",
        f"--add-binary={runtime / 'libvlccore.dll'}{sep}{VLC_BUNDLE_DIR}",
        f"--add-data={runtime / 'plugins'}{sep}{VLC_BUNDLE_DIR}/plugins",
    ]
    return args


def compose_html() -> Path:
    """Build src/web/index.html from index.template.html and src/web/partials/.

    Each partials/<name>.html replaces ``<!-- include:<name> -->`` in the template.
    The output is checked in so ``python src/main.py`` works without a build.
    """
    template_path = SRC / "web" / "index.template.html"
    partials_dir = SRC / "web" / "partials"
    out_path = SRC / "web" / "index.html"
    if not template_path.exists():
        print("compose-html: template missing, leaving index.html untouched")
        return out_path
    text = template_path.read_text(encoding="utf-8")
    for partial in sorted(partials_dir.glob("*.html")):
        marker = f"<!-- include:{partial.stem} -->"
        text = text.replace(marker, partial.read_text(encoding="utf-8").rstrip("\n"))
    out_path.write_text(text, encoding="utf-8")
    print(f"compose-html: wrote {out_path.relative_to(ROOT)}")
    return out_path


def _read_version() -> str:
    """Read the version from `src/version.py` without importing it.

    Only a line that starts with ``__version__`` counts, because the module
    docstring mentions it too.
    """
    text = (SRC / "version.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "0.0.0"


VERSION = _read_version()


def clean_build() -> None:
    for dir_name in ("build", "dist"):
        path = ROOT / dir_name
        if path.exists():
            shutil.rmtree(path)
            print(f"cleaned {path}")
    for spec in ("Yoink.spec",):
        spec_path = ROOT / spec
        if spec_path.exists():
            spec_path.unlink()
            print(f"cleaned {spec_path}")


def build_exe(with_player: bool = True) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    sep = ";" if os.name == "nt" else ":"
    sys.path.insert(0, str(SRC))

    cmd = [
        "pyinstaller",
        "--name=Yoink",
        "--onefile",
        "--windowed",
        "--clean",
        f"--paths={SRC}",
        f"--add-data=src/resources{sep}resources",
        f"--add-data=src/web{sep}web",
        f"--add-data=src/vendor{sep}vendor",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtNetwork",
        "--hidden-import=PyQt6.QtWebEngineWidgets",
        "--hidden-import=PyQt6.QtWebEngineCore",
        "--hidden-import=PyQt6.QtWebChannel",
        "--hidden-import=main_window",
        "--hidden-import=bridge",
        "--hidden-import=workers",
        "--hidden-import=db",
        "--hidden-import=models",
        "--hidden-import=version",
        "--hidden-import=torrents",
        "--hidden-import=torrents.session",
        "--hidden-import=torrents.actions",
        "--hidden-import=torrents.state",
        "--hidden-import=torrents.persistence",
        "--hidden-import=torrents.resume",
        "--hidden-import=torrents.dto",
        "--hidden-import=torrents.streaming",
        "--hidden-import=feeds",
        "--hidden-import=player",
        "--hidden-import=player.runtime",
        "--hidden-import=player.backend",
        "--hidden-import=player.window",
        "--hidden-import=search",
        "--hidden-import=search.enums",
        "--hidden-import=search.dto",
        "--hidden-import=search.ranking",
        "--hidden-import=search.safety",
        "--hidden-import=providers",
        "--hidden-import=providers.yts",
        "--hidden-import=providers.pirate_bay",
        "--hidden-import=providers.torrent_api_py",
        "--hidden-import=providers.tmdb",
        "--hidden-import=providers.health",
        "--hidden-import=utils",
        "--hidden-import=utils.logger",
        "--hidden-import=utils.format",
        "--hidden-import=utils.paths",
        "--hidden-import=utils.magnets",
        "--hidden-import=utils.autostart",
        "--hidden-import=utils.single_instance",
        "--hidden-import=libtorrent",
        "--hidden-import=sqlalchemy",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=aiohttp",
        "--hidden-import=vlc",
    ]
    cmd += vlc_bundle_args(sep, required=with_player)
    cmd.append("src/main.py")
    subprocess.run(cmd, check=True)
    print("PyInstaller build complete -> dist/Yoink.exe")


def build_installer() -> None:
    if os.name != "nt":
        print("installer step skipped (non-Windows host)")
        return
    iss_path = ROOT / "installer" / "yoink.iss"
    if not iss_path.exists():
        print("installer skipped: installer/yoink.iss not found")
        return
    iscc = shutil.which("ISCC") or shutil.which("ISCC.exe")
    if not iscc:
        candidate = Path(r"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe")
        if candidate.exists():
            iscc = str(candidate)
    if not iscc:
        print("installer skipped: Inno Setup (ISCC) not on PATH. Install it from https://jrsoftware.org/isinfo.php")
        return
    print(f"Running Inno Setup: {iscc} {iss_path}")
    subprocess.run([iscc, f"/DAppVersion={VERSION}", str(iss_path)], check=True, cwd=ROOT)
    print("Installer ready in dist/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exe-only",
        action="store_true",
        help="Skip the Inno Setup installer step",
    )
    parser.add_argument(
        "--compose-html",
        action="store_true",
        help="Only re-assemble src/web/index.html from partials and exit",
    )
    parser.add_argument(
        "--no-player",
        action="store_true",
        help="Build without bundling VLC. The in-app player will not work.",
    )
    args = parser.parse_args()

    if args.compose_html:
        compose_html()
        return

    clean_build()
    compose_html()
    build_exe(with_player=not args.no_player)
    if not args.exe_only:
        build_installer()


if __name__ == "__main__":
    main()
