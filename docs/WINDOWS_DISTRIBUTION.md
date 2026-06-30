# Windows Distribution Plan

## Goal

Ship the Torrent App as a Windows desktop application that users can install or run without setting up Python manually.

## Recommended Path

Use PyInstaller first, then wrap the output in an installer once the app is stable.

1. Build a clean Python 3.11 virtual environment.
2. Install dependencies from `requirements.txt`.
3. Package with PyInstaller, including PyQt6, libtorrent, and `src/resources`.
4. Move runtime data to user-writable folders.
5. Smoke test the packaged app on a clean Windows profile.
6. Create an installer with Inno Setup or WiX.
7. Code sign the installer/exe if distributing publicly.

## Runtime Data Locations

Do not store mutable app data next to the executable.

- Database: `%APPDATA%/TorrentApp/torrent.db`
- Logs: `%LOCALAPPDATA%/TorrentApp/logs/`
- Settings: `QSettings` or `%APPDATA%/TorrentApp/settings.json`
- Downloads: user-selected folder, defaulting to `Downloads`

## Build Command During Development

The current repo has `build.py`, so a development build should start with:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD;$PWD\src"
python .\build.py
```

Expect to refine `build.py` or create a checked-in `.spec` file as the UI/resources mature.

## Release Checklist

- App launches from `dist` without the source checkout.
- Qt platform plugins are included.
- App icon appears in the window, taskbar, and installer.
- `libtorrent` imports successfully on a clean machine.
- Database and logs are created in user-writable app data folders.
- Search, add, pause, resume, remove, and open-folder flows work.
- Windows Defender/SmartScreen behavior is understood.
- Installer uninstall removes app files but does not delete user downloads.

## Distribution Options

- Portable zip: fastest for testing, lowest polish.
- Installer: best for normal users; use Inno Setup or WiX.
- Microsoft Store: possible later, but packaging, signing, and policy review are more involved.

## Important Caveat

Unsigned torrent software may trigger extra trust prompts. For public distribution, code signing and a clear website/release page matter.
