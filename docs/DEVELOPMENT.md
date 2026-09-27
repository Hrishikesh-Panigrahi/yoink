# Development

Set up the venv as in the [README](../README.md#how-to-run). `requirements.txt`
also installs the test and lint tools. `make help` lists the Make targets.

## Tests and lint

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

`tests/conftest.py` puts `src/` on `sys.path`, so tests use the same flat
imports as the app (`from torrents import ...`, `from search import search`).
It also points `TORRENT_DB_PATH` at a temp file, so the suite never touches
your real library.

`ruff.toml` holds the lint config: pycodestyle, pyflakes, import order, bugbear
and comprehension rules at a 100-column limit, with `src/vendor/` excluded
because that tree is vendored third-party code. `ruff check . --fix` applies
the mechanical fixes.

## Editing the UI

`src/web/index.html` is generated from `src/web/index.template.html` and the
files in `src/web/partials/`. After editing either, regenerate it:

```powershell
python build.py --compose-html
```

`make run` does this before starting the app.

## Build an exe and installer

```powershell
python build.py
```

That does three things in order:

1. **Composes the HTML**, as above.
2. **Builds `dist/Yoink.exe`** with PyInstaller `--onefile` (installed for you
   if missing), bundling `src/web/`, `src/resources/`, `src/vendor/` and a VLC
   runtime. The exe is portable and runs from anywhere.
3. **Builds `dist/Yoink-Setup-<version>.exe`** with Inno Setup, if `ISCC` is on
   PATH or in its default install folder. Otherwise the step is skipped and the
   exe is still usable.

Flags: `--exe-only` skips the installer, and `--no-player` builds without VLC.
Without that flag the build fails when it can't find a VLC runtime, rather
than shipping a Play button that does nothing. It looks in `YOINK_VLC_DIR`,
then `C:\Program Files\VideoLAN\VLC`. The version comes from `src/version.py`.

The installer (`installer/yoink.iss`) is per-user and x64 only, so Windows does
not ask for an administrator password. It can optionally add a desktop shortcut
and register `magnet:` links and `.torrent` files, all under
`HKCU\Software\Classes`. Uninstalling removes the program files and those
associations, and leaves downloads and the data folder alone.

The build is unsigned, so SmartScreen warns the first time you run it.

## Where Yoink keeps its data

Nothing mutable is written next to the code or the executable.

| What | Where |
| --- | --- |
| Database and settings | `%LOCALAPPDATA%\Yoink\yoink.db` |
| Logs | `%LOCALAPPDATA%\Yoink\logs\yoink.log` |
| Fast-resume data | `%LOCALAPPDATA%\Yoink\resume\<infohash>.fastresume` |
| Portable VLC, if you add one | `%LOCALAPPDATA%\Yoink\vlc\` |
| Downloads | user-chosen folder, defaults to `Downloads` |

`src/utils/paths.py` resolves these, falling back to `%APPDATA%` and then
`~/AppData/Local` if `%LOCALAPPDATA%` is missing. `TORRENT_DB_PATH` overrides
the database path.

## Layout tour

```
src/
  main.py                entrypoint, exception logging
  main_window.py         QMainWindow, system tray, web view host
  workers.py             QThread workers behind the bridge's async signals
  db.py                  SQLite helpers (init_db, get/set_setting, ...)
  models.py              SQLAlchemy ORM (Setting, SavedTorrent)
  version.py             __version__ and the repo URL

  bridge/                JS <-> Python RPC surface, split by area
    core.py              Bridge(QObject), signals, worker wiring
    search_slots.py      search, provider health, history
    torrents_slots.py    add/pause/resume/remove, per-file priorities, labels
    player_slots.py      player status, play a download or a magnet in app
    settings_slots.py    settings, proxy, schedule, import/export
    system_slots.py      folders, notifications, about info, command palette
    feeds_slots.py       RSS subscriptions

  torrents/              libtorrent layer (functions, one small Session class)
    session.py           create_session / stop_session / set_save_path
    actions.py           add_magnet / add_torrent_file / pause / resume / remove
    state.py             list_torrents -> TorrentSnapshot DTOs
    streaming.py         sequential order and head/tail deadlines for playback
    persistence.py       restore torrents on startup
    resume.py            fast-resume file read/write
    watch.py             watch-folder discovery
    dto.py               TorrentSnapshot, TorrentFile, NetworkStats, StreamPlan, ...

  player/                in-app video playback over libvlc
    runtime.py           find a VLC runtime, import vlc safely
    source.py            feed libvlc from a file that is still growing
    backend.py           thin MediaPlayer wrapper
    window.py            the player window and its controls

  search/                search orchestrator (function `search()`)
    enums.py             ProviderMode, Region, Category, Quality, SortBy
    dto.py               SearchResult, SearchOptions, SearchPage
    ranking.py           query expansion, health score, dedupe
    safety.py            heuristic risk flags for results

  providers/             one module per source, all functions
    yts.py               search_yts
    pirate_bay.py        search_pirate_bay
    torrent_api_py.py    vendored multi-site adapter
    health.py            ping_all, graded into three bands
    tmdb.py              poster/rating/plot enrichment, cached

  feeds/                 RSS configs, seen-item tracking, fetching

  utils/                 shared stateless helpers
    format.py            format_size / format_speed / format_eta
    paths.py             normalize_path, user-writable app data dirs
    magnets.py           build_magnet
    logger.py            setup_logger
    resolver.py          DNS-over-HTTPS for provider hostnames
    autostart.py         launch at login
    single_instance.py   single-instance guard and CLI handoff

  web/                   the embedded UI: js/main.js, css/, and partials/ that
                         build.py composes into index.html
  resources/             app icon and its generator
  vendor/torrent_api_py/ upstream scrapers, untouched
```

Classes are reserved for things frameworks or native handles require: PyQt
subclasses, the SQLAlchemy ORM, the one libtorrent `Session` dataclass, and the
libvlc wrappers in `player/`. Everything else is a module-level function, with
enums for fixed value sets and frozen dataclass DTOs for structured data.
