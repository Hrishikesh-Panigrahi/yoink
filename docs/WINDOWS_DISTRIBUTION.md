# Windows Distribution Plan

## Goal

Ship Yoink as a Windows desktop application that users can install or run without setting up Python manually.

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

- Database: `%LOCALAPPDATA%/Yoink/yoink.db`
- Logs: `%LOCALAPPDATA%/Yoink/logs/`
- Settings: `%LOCALAPPDATA%/Yoink/yoink.db`
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
- GitHub Releases: source of truth for downloadable `Yoink.exe`, installer, and checksums.
- GitHub Pages: public download page that links to the latest release.
- Microsoft Store: possible later, but packaging, signing, and policy review are more involved.

## GitHub Hosting

1. Bump `src/version.py`.
2. Push a tag such as `v2.0.0`.
3. Let `.github/workflows/release.yml` build and publish release assets.
4. Enable GitHub Pages from the `docs/` folder on the default branch.
5. Point users to the Pages site for installation instructions and the latest release link.

## Important Caveat

Unsigned torrent software may trigger extra trust prompts. For public distribution, code signing and a clear website/release page matter.

## Code Signing Notes

- Sign `dist/Yoink.exe` and `dist/Yoink-Setup-*.exe` before uploading public release assets.
- Sign before the workflow's "Add stable-named installer alias" step, or `Yoink-Setup.exe`
  ends up being a copy of the unsigned build.
- Store signing credentials as GitHub Actions secrets; do not commit certificate files or passwords.
- Re-generate `SHA256SUMS.txt` after signing so hashes match the published binaries.
- If signing is not available yet, call that out on the download page and release notes so users know why Windows may show SmartScreen warnings.
