#!/usr/bin/env python3
"""Build Yoink for Windows.

Stages:
    1. clean   — wipe `build/`, `dist/`, and stale spec files.
    2. exe     — run PyInstaller --onefile to produce `dist/Yoink.exe`.
    3. installer (optional, Windows only) — invoke Inno Setup with
       `installer/yoink.iss` to produce `dist/Yoink-Setup-<ver>.exe`.

Usage:
    python build.py            # full pipeline (exe + installer if ISCC found)
    python build.py --exe-only # skip the installer step
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


def compose_html() -> Path:
    """Assemble src/web/index.html from index.template.html + partials.

    Each partial in src/web/partials/<name>.html replaces the matching
    ``<!-- include:<name> -->`` placeholder in the template.

    Idempotent and safe to run before PyInstaller; the generated file
    is checked in so direct ``python src/main.py`` keeps working.
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
    """Read version from `src/version.py` without importing it."""
    text = (SRC / "version.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__"):
            return line.split("=")[1].strip().strip('"').strip("'")
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


def build_exe() -> None:
    """Run PyInstaller to produce the standalone Yoink.exe."""
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
        # Stable PyQt6 imports
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtNetwork",
        "--hidden-import=PyQt6.QtWebEngineWidgets",
        "--hidden-import=PyQt6.QtWebEngineCore",
        "--hidden-import=PyQt6.QtWebChannel",
        # First-party modules
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
        "--hidden-import=utils.updater",
        # Third-party
        "--hidden-import=libtorrent",
        "--hidden-import=sqlalchemy",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=PIL",
        "--hidden-import=aiohttp",
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)
    print("PyInstaller build complete -> dist/Yoink.exe")


def build_installer() -> None:
    """Invoke Inno Setup if available to produce the Windows installer."""
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
    parser.add_argument("--exe-only", action="store_true", help="Skip the Inno Setup installer step")
    parser.add_argument("--compose-html", action="store_true", help="Only re-assemble src/web/index.html from partials and exit")
    args = parser.parse_args()

    if args.compose_html:
        compose_html()
        return

    clean_build()
    compose_html()
    build_exe()
    if not args.exe_only:
        build_installer()


if __name__ == "__main__":
    main()
