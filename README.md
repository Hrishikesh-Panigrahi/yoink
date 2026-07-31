# Yoink

> Just yoink it from the swarm.

Yoink is a modern desktop torrent client. The shell is PyQt6, the UI is a web
view (HTML/CSS/JS) wired to Python through `QWebChannel`, and the torrent engine
is libtorrent. Search hits YTS and The Pirate Bay by default, with optional
multi-site scraping via a vendored copy of
[Torrent-Api-py](https://github.com/Ryuk-me/Torrent-Api-py).

## Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
$env:PYTHONPATH = "$PWD;$PWD\src"
python src\main.py
```

On macOS/Linux replace the venv activation and use `PYTHONPATH=$PWD:$PWD/src`.

## Run the tests

```powershell
.venv\Scripts\python.exe -m pytest
```

`tests/conftest.py` puts `src/` on `sys.path`, so tests use the same flat
imports as the app (`from torrents import ...`, `from search import search`).

## Package for Windows

```powershell
python build.py
```

This wraps PyInstaller and produces `dist/Yoink.exe`. The build script bundles
`src/web/`, `src/resources/`, and `src/vendor/` alongside the executable. See
[`docs/WINDOWS_DISTRIBUTION.md`](docs/WINDOWS_DISTRIBUTION.md) for installer
notes.

## Download and hosting

Public Windows builds are hosted on
[GitHub Releases](https://github.com/Hrishikesh-Panigrahi/yoink/releases/latest).
Pushing a `v*` tag runs `.github/workflows/release.yml`, which publishes four
assets:

| Asset | Purpose |
| --- | --- |
| `Yoink-Setup.exe` | Stable filename. What the landing page links to. |
| `Yoink-Setup-<version>.exe` | Same installer, version-stamped for archiving. |
| `Yoink.exe` | Portable single-file build, no installer. |
| `SHA256SUMS.txt` | Checksums for all three binaries. |

`Yoink-Setup.exe` is a copy of the versioned installer that exists purely so the
filename never changes. That is what makes GitHub's permanent redirect usable as
a one-click download:

```
https://github.com/Hrishikesh-Panigrahi/yoink/releases/latest/download/Yoink-Setup.exe
https://github.com/Hrishikesh-Panigrahi/yoink/releases/latest/download/Yoink.exe
```

These always resolve to the newest release, and GitHub serves them with
`Content-Disposition: attachment`, so a click downloads the binary instead of
navigating to a web page. Do not hardcode the version-stamped name anywhere
public — it breaks on every release.

### Landing page

The public site is a single self-contained file,
[`docs/index.html`](docs/index.html) — no build step, no dependencies. To host it:

1. Repo **Settings → Pages**, set source to **Deploy from a branch**.
2. Branch `main`, folder `/docs`. Save.
3. The site goes live at `https://hrishikesh-panigrahi.github.io/yoink/`.

The download buttons carry the static URLs above, so they work with JavaScript
disabled. On load, a small script queries the GitHub Releases API to fill in the
real version number, installer size, and release date, and retargets the buttons
at the exact assets on the latest release. If that request fails or is
rate-limited, the static links still work.

Because the buttons are wired to the stable filename, **the landing page needs
one tagged release to exist before the download works.** Bump `src/version.py`,
then push a tag:

```bash
git tag v2.0.1 && git push origin v2.0.1
```

## Legal note

Yoink is a torrent client. It does not host, bundle, or endorse copyrighted
content. You are responsible for using torrents and magnet links legally in your
region.

## Layout tour

```
src/
  main.py              # entrypoint
  main_window.py       # QMainWindow + system tray + web view host
  bridge.py            # Bridge(QObject) — JS<->Python RPC surface
  workers.py           # SearchWorker, DownloadsPollWorker, NetworkSpeedWorker
  db.py                # SQLite helpers (init_db, get/set_setting, ...)
  models.py            # SQLAlchemy ORM (Setting, SavedTorrent)

  torrents/            # libtorrent layer (function-based, one tiny Session class)
    session.py         #   create_session / stop_session / set_save_path
    actions.py         #   add_magnet / add_torrent_file / pause / resume / remove
    state.py           #   list_torrents → TorrentSnapshot DTOs
    persistence.py     #   load_saved (restore torrents on startup)
    dto.py             #   TorrentSnapshot, NetworkStats

  search/              # search orchestrator (function `search()`)
    enums.py           #   ProviderMode, Region, Category
    dto.py             #   SearchResult, SearchOptions, SearchPage
    ranking.py         #   query expansion + scoring + dedupe

  providers/           # one module per source, all functions
    yts.py             #   search_yts
    pirate_bay.py      #   search_pirate_bay
    torrent_api_py.py  #   vendored multi-site adapter

  utils/               # shared stateless helpers
    format.py          #   format_size / format_speed / format_eta
    paths.py           #   normalize_path / user-writable app data paths
    magnets.py         #   build_magnet
    logger.py          #   setup_logger

  web/                 # HTML/CSS/JS for the embedded UI
  resources/           # app icon + icon generator
  vendor/torrent_api_py/  # upstream scrapers (untouched)
```

Classes are reserved for things Python's frameworks require (PyQt subclasses,
SQLAlchemy ORM, the one libtorrent `Session` dataclass). Everything else is a
module-level function with enums for fixed value sets and frozen dataclass DTOs
for structured data.
