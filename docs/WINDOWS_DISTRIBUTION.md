# Windows distribution

How Yoink gets from source to something a person can double-click. This
describes the pipeline as it stands, not a plan.

## The pipeline

`build.py` does three things in order:

1. **Compose the HTML.** `src/web/index.html` is rebuilt from
   `src/web/index.template.html` and the partials in `src/web/partials/`.
2. **Build the exe.** PyInstaller runs with `--onefile` and produces
   `dist/Yoink.exe`, bundling `src/web/`, `src/resources/` and `src/vendor/`.
3. **Build the installer.** If `ISCC` (Inno Setup) is on PATH, it compiles
   `installer/yoink.iss` into `dist/Yoink-Setup-<version>.exe`. If it isn't,
   the step is skipped with a message and the exe is still usable.

```powershell
python build.py             # everything
python build.py --exe-only  # skip the installer
python build.py --compose-html  # just regenerate src/web/index.html
```

The version comes from `src/version.py`, which is the single source of truth
for `build.py`, `setup.py`, the About panel and the updater.

## What the installer does

`installer/yoink.iss` is a per-user install: `PrivilegesRequired=lowest`, so
Windows does not prompt for an administrator password. It is x64 only.

Optional tasks the user can tick:

- a desktop shortcut,
- register `magnet:` links to open in Yoink,
- register `.torrent` files to open in Yoink.

Both associations are written under `HKCU\Software\Classes` and removed on
uninstall. Uninstalling removes the program files. It does not touch downloads
or the app data folder.

## Runtime data locations

Nothing mutable is written next to the executable.

| What | Where |
| --- | --- |
| Database and settings | `%LOCALAPPDATA%\Yoink\yoink.db` |
| Logs | `%LOCALAPPDATA%\Yoink\logs\yoink.log` |
| Fast-resume data | `%LOCALAPPDATA%\Yoink\resume\<infohash>.fastresume` |
| Downloads | user-chosen folder, defaults to `Downloads` |

`src/utils/paths.py` resolves these, falling back to `%APPDATA%` and then
`~/AppData/Local` if `%LOCALAPPDATA%` is missing.

## Releasing

1. Bump `__version__` in `src/version.py`.
2. Commit, then push a tag: `git tag v2.0.1 && git push origin v2.0.1`.
3. `.github/workflows/release.yml` runs the tests, builds the exe, installs
   Inno Setup, builds the installer, copies it to the stable filename
   `Yoink-Setup.exe`, writes `SHA256SUMS.txt` and publishes the release.

If a `.apk` is sitting in `dist/` when the checksum step runs, it is hashed and
published with everything else. Nothing here builds one; see `TODO.md`. You can
also just attach an APK to the finished release by hand, in which case it skips
the checksum file. Either way the landing page notices it and shows an Android
download button.

The workflow also runs on `workflow_dispatch`, but only tag pushes publish a
release. See the README for what each asset is for and why the stable filename
exists.

## Release checklist

- The app launches from `dist` on a machine with no source checkout.
- Qt platform plugins are present and the window actually appears.
- `libtorrent` imports on a clean machine.
- The app icon shows in the window, taskbar and installer.
- Database and logs are created under `%LOCALAPPDATA%`.
- Search, add, pause, resume, remove and open-folder all work.
- A `magnet:` link opens the running instance rather than a second copy.
- Uninstall leaves downloads alone.

## Code signing

Not done yet. Until it is, SmartScreen will warn on first run, which the
download page explains rather than hides.

When a certificate is available:

- Sign `dist/Yoink.exe` and `dist/Yoink-Setup-*.exe` before uploading.
- Sign *before* the workflow's "Add stable-named installer alias" step, or
  `Yoink-Setup.exe` ends up being a copy of the unsigned build.
- Regenerate `SHA256SUMS.txt` after signing, or the published hashes won't
  match the published binaries.
- Keep credentials in GitHub Actions secrets. Don't commit certificates.

## Other distribution options

- **Portable exe.** Already shipped as `Yoink.exe`. Runs from anywhere,
  including a USB stick.
- **Android.** Not built. It would be a separate codebase rather than another
  target for this one, and APK signing is its own thing (`apksigner`, not
  Authenticode). See `TODO.md`.
- **Microsoft Store.** Possible later. Packaging, signing and policy review
  are all more involved than the current setup.
