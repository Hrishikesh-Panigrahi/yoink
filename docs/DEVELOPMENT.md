# Development

Set up the virtual environment as described in the
[README](../README.md#how-to-run). `requirements.txt` also installs the test
and lint tools. Run `make help` to see the Make targets.

## Tests and lint

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

`tests/conftest.py` puts `src/` on the import path, so the tests import things
the same way the app does (`from torrents import ...`, `from search import search`).
It also points `TORRENT_DB_PATH` at a temporary file, so running the tests never
touches your real library.

The lint settings are in `ruff.toml`. Lines can be up to 100 characters, and
`src/vendor/` is skipped because it's third-party code we copied in.
`ruff check . --fix` fixes the simple things for you.

## Working on the UI

`src/web/index.html` is generated. The real sources are
`src/web/index.template.html` and the files in `src/web/partials/`. After
changing any of them, rebuild the page:

```powershell
python build.py --compose-html
```

`make run` does this for you before starting the app.

The JavaScript in `src/web/js/` is split into one module per feature:
`search.js`, `downloads.js`, `settings.js` and so on. Each module sets up its
own buttons in a `bind...Events()` function and listens to the Python side in a
`connect...Signals()` function. `main.js` just calls them in the right order
when the page loads. Shared state is in `state.js` and cached page elements are
in `dom.js`.

The styles in `src/web/css/` follow the same idea, with one file per area.
`styles.css` imports them in order. That order matters: when two rules are
equally specific, the one in the later file wins, so `responsive.css` has to
stay last.

## Build an exe and installer

```powershell
python build.py
```

This does three things:

1. Rebuilds the HTML, as above.
2. Builds `dist/Yoink.exe` with PyInstaller (it installs PyInstaller if it's
   missing). The exe includes `src/web/`, `src/resources/`, `src/vendor/` and
   VLC, and runs from anywhere without installing.
3. Builds `dist/Yoink-Setup-<version>.exe` with Inno Setup, if it can find
   `ISCC`. If it can't, it skips this step and you still have the exe.

Use `--exe-only` to skip the installer, or `--no-player` to build without VLC.
Without `--no-player`, the build stops if it can't find VLC, so you never end up
with a Play button that doesn't work. It looks in `YOINK_VLC_DIR` and then in
`C:\Program Files\VideoLAN\VLC`. The version number comes from
`src/version.py`.

The installer (`installer/yoink.iss`) installs for the current user only, so it
doesn't ask for an admin password. It's 64-bit only. It can add a desktop
shortcut and make `magnet:` links and `.torrent` files open in Yoink, all under
`HKCU\Software\Classes`. Uninstalling removes the program and those links, and
leaves your downloads and data folder alone.

The build isn't signed, so Windows SmartScreen will warn you the first time you
run it.

## Where Yoink keeps its data

Yoink never writes next to the code or the exe.

| What | Where |
| --- | --- |
| Database and settings | `%LOCALAPPDATA%\Yoink\yoink.db` |
| Logs | `%LOCALAPPDATA%\Yoink\logs\yoink.log` |
| Download progress (fast-resume) | `%LOCALAPPDATA%\Yoink\resume\<infohash>.fastresume` |
| Portable VLC, if you add one | `%LOCALAPPDATA%\Yoink\vlc\` |
| Downloads | the folder you choose, `Downloads` by default |

These paths come from `src/utils/paths.py`. If `%LOCALAPPDATA%` isn't set, it
uses `%APPDATA%`, and then `~/AppData/Local`. `TORRENT_DB_PATH` overrides the
database location.

## Where the code lives

```
src/
  main.py                starts the app and logs uncaught errors
  main_window.py         the main window, tray icon and web view
  workers.py             background threads behind the bridge
  db.py                  SQLite helpers (init_db, get/set_setting, ...)
  models.py              database tables (Setting, SavedTorrent)
  feeds.py               RSS feed settings, what's been seen, fetching
  version.py             version number and repo URL

  bridge/                everything the web page can call in Python, by area
    core.py              the Bridge object, its signals and workers
    search_slots.py      searching, source health, search history
    torrents_slots.py    add, pause, resume, remove, file choices, labels
    player_slots.py      player status, playing a download or a magnet
    settings_slots.py    settings, proxy, schedule, import and export
    system_slots.py      folders, notifications, About info, command palette
    feeds_slots.py       RSS subscriptions

  torrents/              the libtorrent side
    session.py           create_session / stop_session / set_save_path
    actions.py           add_magnet / add_torrent_file / pause / resume / remove
    state.py             list_torrents, which returns TorrentSnapshot objects
    streaming.py         downloading in order for playback
    persistence.py       restoring torrents at startup
    resume.py            reading and writing fast-resume files
    watch.py             finding new files in the watch folder
    dto.py               TorrentSnapshot, TorrentFile, NetworkStats, StreamPlan, ...

  player/                the video player, built on libVLC
    runtime.py           finding VLC and importing it safely
    source.py            feeding VLC from a file that's still downloading
    backend.py           a small wrapper around VLC's media player
    window.py            the player window and its controls

  search/                search() and everything it uses
    enums.py             ProviderMode, Region, Category, Quality, SortBy
    dto.py               SearchResult, SearchOptions, SearchPage
    ranking.py           query expansion, scoring, removing duplicates
    categories.py        working out a result's category when a site can't filter
    safety.py            warnings for suspicious results

  providers/             one module per source
    pirate_bay.py        search_pirate_bay
    torrent_api_py.py    the multi-site scrapers in vendor/
    health.py            ping_all, which marks each source working, slow or down
    tmdb.py              posters, ratings and plots, cached

  utils/                 small shared helpers
    format.py            format_size / format_speed / format_eta
    paths.py             normalize_path and the app data folders
    magnets.py           build_magnet
    logger.py            setup_logger
    resolver.py          DNS-over-HTTPS for source hostnames
    proxy.py             sending searches through the proxy from Settings
    autostart.py         launch at login
    single_instance.py   keeping to one running copy and passing links to it

  web/                   the page shown inside the window
    index.template.html  the page shell; build.py fills in partials/
    js/                  one module per feature, main.js starts them
    css/                 one stylesheet per area, loaded in order by styles.css
  resources/             the app icon and the script that draws it
  vendor/torrent_api_py/ third-party scrapers, left as they came
```

Most of the code is plain functions. Classes are only used where a framework
needs one (PyQt windows, threads and the bridge, the database models), for the
small `Session` that holds libtorrent handles, and for the VLC wrappers. Fixed
sets of values are enums, and data passed between modules uses frozen
dataclasses.
