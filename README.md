# Yoink

> Just yoink it from the swarm.

Yoink is a desktop torrent client for Windows. The shell is PyQt6, the UI is
HTML/CSS/JS in a web view wired to Python over `QWebChannel`, and the torrent
engine is libtorrent. Search fans out across the sites enabled in Settings →
Sources through a vendored copy of
[Torrent-Api-py](https://github.com/Ryuk-me/Torrent-Api-py), and falls back to
The Pirate Bay's API when those return nothing.

**Yoink is self-hosted.** There are no published downloads: you run it from
source, or build your own exe and installer on your own machine. Both are
covered below.

Known outstanding work: [`TODO.md`](TODO.md)

## Features

Everything below is implemented and reachable from the UI.

### Search

- **Two provider modes.** `multi` searches the vendored scrapers you have
  enabled and is the default ("All my enabled sites"). `stable` queries The
  Pirate Bay's API directly and is the fastest. YTS can be switched on as a
  stable source, but is off by default (see [Sources and DNS](#sources-and-dns)).
- **Filters.** Region (Bollywood, Hollywood, South Indian, Korean, anime),
  category (movies, TV, anime, music, games, apps, books), quality, and sort by
  relevance, seeds, size or newest.
- **Health ranking.** Results are scored on seeders, quality and source weight,
  then deduplicated by infohash so one release doesn't appear five times.
- **Provider health checks.** Every source can be pinged with a small test
  search and graded into three bands, so you can see what's reachable and turn
  off what isn't. Sources can be enabled individually.
- **Safety flags.** Results are scanned for common red flags: an `.exe` inside
  something claiming to be a film, a file far too small for its stated quality,
  password-protected archives.
- **TMDB metadata.** With a free API key, results gain posters, backdrops,
  ratings, runtime, genres, plot and a trailer link. Responses are cached.
- **Search history**, recalled as you type.

### Transfers

- Add by magnet link, `.torrent` file, or drag and drop.
- Per-file priorities, so you can skip the extras inside a torrent.
- Pause and resume individually or across the whole queue.
- Move a torrent to a different folder after it has started.
- Remove with or without deleting the data.
- Labels for grouping a library.
- Fast-resume data is written per torrent, so progress survives a restart.
- Open the finished file or reveal it in Explorer.
- Play a video while it is still downloading (see
  [below](#playing-a-file-while-it-downloads)).

### Automation

- **Watch folder.** Drop a `.torrent` into a directory and it gets added.
- **RSS feeds.** Subscribe with an optional title regex and a minimum-seeder
  floor. Seen items are tracked so nothing is added twice.
- **Clipboard watcher.** Copy a magnet link anywhere and Yoink offers to take it.
- **Scheduled bandwidth.** Apply quieter caps during a chosen window.
- **File associations.** The installer can register `magnet:` links and
  `.torrent` files. A single-instance guard hands the path to the running
  window instead of opening a second one.

### Limits

Global download and upload caps, a limit on how many torrents download and seed
at once, and a seed ratio limit that pauses a torrent once it is reached.

### Application

- Eight themes. Minimise to tray and keep seeding.
- Native notifications when a download finishes.
- Optional launch at login.
- Command palette and keyboard shortcuts.
- Export and import settings.
- Proxy support (`http`, `https`, `socks5`) with a custom user agent.
- Settings live in a SQLite file under `%LOCALAPPDATA%\Yoink\`. No account, no
  telemetry.

## How to run

You need Windows 10 or 11 (x64) and Python 3.10 or newer (CI tests on 3.11). VLC is optional and
only needed for the in-app player.

```powershell
git clone https://github.com/Hrishikesh-Panigrahi/yoink.git
cd yoink
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
$env:PYTHONPATH = "$PWD;$PWD\src"
python src\main.py
```

Add `--minimized` to start in the tray with no window. On macOS/Linux, activate
the venv the usual way and use `PYTHONPATH=$PWD:$PWD/src`.

With GNU Make installed, `make install` then `make run` does the same thing.
`make help` lists the other targets (`test`, `lint`, `build`, `clean`, ...).

A run from source uses the same library as any other copy on the machine,
`%LOCALAPPDATA%\Yoink\yoink.db`. To keep a trial run away from it, point
`TORRENT_DB_PATH` at another file first:

```powershell
$env:TORRENT_DB_PATH = "$env:TEMP\yoink-dev.db"
```

`src/web/index.html` is generated from `src/web/index.template.html` and the
files in `src/web/partials/`. If you edit a partial, regenerate it:

```powershell
python build.py --compose-html
```

### Where Yoink keeps its data

Nothing mutable is written next to the code or the executable.

| What | Where |
| --- | --- |
| Database and settings | `%LOCALAPPDATA%\Yoink\yoink.db` |
| Logs | `%LOCALAPPDATA%\Yoink\logs\yoink.log` |
| Fast-resume data | `%LOCALAPPDATA%\Yoink\resume\<infohash>.fastresume` |
| Downloads | user-chosen folder, defaults to `Downloads` |

`src/utils/paths.py` resolves these, falling back to `%APPDATA%` and then
`~/AppData/Local` if `%LOCALAPPDATA%` is missing.

## Build your own exe and installer

```powershell
python build.py
```

That does three things in order:

1. **Composes the HTML** from the partials, as above.
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

## Development

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

`.github/workflows/ci.yml` runs both on pull requests and on pushes to `main`:
ruff on Linux, and the test suite on Windows with Python 3.11, as separate jobs.

## Sources and DNS

The default search goes to the vendored sites enabled in Settings → Sources,
which are 1337x, TorrentGalaxy and Nyaa out of the box, and falls back to The
Pirate Bay if they return nothing. "Stable APIs only" in the source filter
skips the vendored sites.

YTS is **off** by default: `yts.mx` no longer publishes an A record, and leaving
it on cost every search two 10-second connect timeouts before any results
appeared.

Some networks answer DNS for torrent indexes with a sinkhole address instead of
the real one, which makes every source look permanently offline. Yoink resolves
source hostnames over DNS-over-HTTPS (Cloudflare, then Google) rather than
trusting the local resolver — on one such connection that took reachable
providers from 2 to 11. Turn it off in Settings → Library & app behavior to use
your system resolver.

It works by replacing `socket.getaddrinfo` (see
[`src/utils/resolver.py`](src/utils/resolver.py)), not by rewriting URLs to raw
IPs — the latter breaks SNI, the `Host` header and certificate validation.

DNS is not a cure-all. A site blocked at the TLS layer resets the connection
even once the address is right, and one behind DDoS-Guard or Cloudflare returns
an interstitial rather than results. For those, use the proxy setting in
Settings, or see the Torznab note in [TODO.md](TODO.md).

## Playing a file while it downloads

A **Play** button appears on any search result with a magnet, and on any
download whose torrent contains a video. From a search result Yoink adds the
magnet, waits for the file list, switches to sequential pieces and buffers the
head before opening the player — the button reports which of those it is on.

The download-row button behaves the same way once the torrent is already added.
It switches libtorrent to sequential order, deadlines the head *and* the tail of
the file, and opens the file in an in-app window — you do not have to wait for
the download to finish.

The tail is prioritised alongside the head on purpose: MP4 keeps its `moov`
index at the end unless the file was written for streaming, and Matroska keeps
its cues there, so a player that cannot see the tail reports an unknown duration
and refuses to seek.

Playing a file that is still downloading needs more than sequential pieces.
VLC's ordinary file access reports end-of-stream at the last byte on disk, so
opening a torrent at 25% plays exactly 25% and stops — measured, not assumed.
Yoink therefore feeds VLC through `libvlc_media_new_callbacks`
(`src/player/source.py`), whose read callback blocks at the current end of the
file and waits for the missing bytes. The torrent's final size is handed to VLC
as the real stream length, so duration and seeking behave from the start.

Playback is libVLC via [`python-vlc`](https://pypi.org/project/python-vlc/).
That package is only a ctypes binding — it needs an actual VLC runtime, which an
exe from `build.py` carries inside it. Running from source, Yoink looks for one
in this order:

1. `YOINK_VLC_DIR`, if you point it at a folder holding `libvlc.dll` and
   `plugins/`.
2. The copy bundled inside a frozen build.
3. A portable copy under `%LOCALAPPDATA%\Yoink\vlc` — installing VLC properly
   needs administrator rights, and unzipping VLC's official
   [portable build](https://www.videolan.org/vlc/download-windows.html) here
   does not.
4. An installed VLC, via the registry then `C:\Program Files\VideoLAN\VLC`.

With none of those, everything else works and the Play button simply stays
hidden; `getPlayerStatus` reports why.

QtMultimedia was the alternative and was rejected: on Windows it goes through
Media Foundation, which is patchy on exactly the MKV, HEVC and AC3 combinations
torrents ship. The cost of libVLC is roughly 40-50 MB of plugins in the build.

## Legal note

Yoink is a torrent client. It does not host, bundle, or endorse copyrighted
content. You are responsible for using torrents and magnet links legally in your
region.

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
    dto.py               TorrentSnapshot, NetworkStats

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

Classes are reserved for things Python's frameworks require (PyQt subclasses,
SQLAlchemy ORM, the one libtorrent `Session` dataclass). Everything else is a
module-level function, with enums for fixed value sets and frozen dataclass DTOs
for structured data.
