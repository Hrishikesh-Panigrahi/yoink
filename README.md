# Yoink

> Just yoink it from the swarm.

Yoink is a desktop torrent client for Windows. The shell is PyQt6, the UI is
HTML/CSS/JS in a web view wired to Python over `QWebChannel`, and the torrent
engine is libtorrent. Search hits YTS and The Pirate Bay directly by default,
with optional multi-site scraping through a vendored copy of
[Torrent-Api-py](https://github.com/Ryuk-me/Torrent-Api-py).

Public site and downloads: <https://hrishikesh-panigrahi.github.io/yoink/>
Known outstanding work: [`TODO.md`](TODO.md)

## Features

Everything below is implemented and reachable from the UI.

### Search

- **Two provider modes.** `stable` queries the YTS and Pirate Bay APIs directly
  and is the default. `multi` fans out across the vendored scrapers.
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
- Update check against GitHub Releases.
- Settings live in a SQLite file under `%LOCALAPPDATA%\Yoink\`. No account, no
  telemetry.

## Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
$env:PYTHONPATH = "$PWD;$PWD\src"
python src\main.py
```

On macOS/Linux, activate the venv the usual way and use
`PYTHONPATH=$PWD:$PWD/src`.

`src/web/index.html` is generated from `src/web/index.template.html` and the
files in `src/web/partials/`. If you edit a partial, regenerate it:

```powershell
python build.py --compose-html
```

## Make targets

There is a `Makefile` if you prefer it. `make help` lists everything; the useful
ones are `install`, `run`, `compose-html`, `test`, `lint`, `build` and `clean`.

## Run the tests

```powershell
.venv\Scripts\python.exe -m pytest
```

`tests/conftest.py` puts `src/` on `sys.path`, so tests use the same flat
imports as the app (`from torrents import ...`, `from search import search`).

`.github/workflows/ci.yml` runs the same suite on Windows with Python 3.11 on
every push. The release workflow runs it too, so a failing test blocks a
release.

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check .
```

`ruff.toml` holds the config: pycodestyle, pyflakes, import order, bugbear and
comprehension rules at a 100-column limit, with `src/vendor/` excluded because
that tree is vendored third-party code. `ruff check . --fix` applies the
mechanical fixes. CI runs the same check as its own job, so lint and test
failures show up as separate signals.

## Package for Windows

```powershell
python build.py
```

That composes the HTML, runs PyInstaller with `--onefile` to produce
`dist/Yoink.exe`, then builds `dist/Yoink-Setup-<version>.exe` with Inno Setup
if `ISCC` is on PATH. It bundles `src/web/`, `src/resources/` and `src/vendor/`.
Pass `--exe-only` to skip the installer step. See
[`docs/WINDOWS_DISTRIBUTION.md`](docs/WINDOWS_DISTRIBUTION.md) for the runtime
data layout, signing notes and the release checklist.

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
| `SHA256SUMS.txt` | Checksums for every binary in the release. |

An Android APK can ride along too. Nothing in this repo builds one, so it has
to come from elsewhere: either drop it into `dist/` before the release job
reaches its checksum step, or attach it to the published release by hand. Either
way it gets picked up, and if it's in `dist/` it lands in `SHA256SUMS.txt` with
the rest.

The landing page keeps its Android button hidden and only shows it when the
newest release actually contains a `.apk`, so a Windows-only release doesn't
leave a dead button on the site. Nothing to edit on the page when you add one.

`Yoink-Setup.exe` is just a copy of the versioned installer. It exists so there
is one filename that never changes, which lets these URLs work forever:

```
https://github.com/Hrishikesh-Panigrahi/yoink/releases/latest/download/Yoink-Setup.exe
https://github.com/Hrishikesh-Panigrahi/yoink/releases/latest/download/Yoink.exe
```

They redirect to the newest release, and GitHub sends them with
`Content-Disposition: attachment`, so clicking one downloads the file rather
than opening a page. Don't put the version-stamped name in any public link. It
breaks the next time you tag.

### Landing page

The site is one file, [`docs/index.html`](docs/index.html). No build step, no
dependencies. To host it:

1. **Settings → Pages**, source **Deploy from a branch**.
2. Branch `main`, folder `/docs`. Save.
3. It goes live at `https://hrishikesh-panigrahi.github.io/yoink/`.

The download buttons use the static URLs above, so they work without
JavaScript. On load a script hits the Releases API to fill in the version,
file size and date, and repoints the buttons at the exact assets. If that call
fails or gets rate-limited nothing breaks; the static links still work.

Note that **the download only works once you have a tagged release**, since
`Yoink-Setup.exe` doesn't exist until the workflow builds it. Bump
`src/version.py` and push a tag:

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
  main.py                entrypoint
  main_window.py         QMainWindow, system tray, web view host
  workers.py             QThread workers behind the bridge's async signals
  db.py                  SQLite helpers (init_db, get/set_setting, ...)
  models.py              SQLAlchemy ORM (Setting, SavedTorrent)
  version.py             __version__, app name, repo and release API URLs

  bridge/                JS <-> Python RPC surface, split by area
    core.py              Bridge(QObject), signals, worker wiring
    search_slots.py      search, provider health, history
    torrents_slots.py    add/pause/resume/remove, per-file priorities, labels
    settings_slots.py    settings, proxy, schedule, import/export
    system_slots.py      folders, notifications, updates, command palette
    feeds_slots.py       RSS subscriptions

  torrents/              libtorrent layer (functions, one small Session class)
    session.py           create_session / stop_session / set_save_path
    actions.py           add_magnet / add_torrent_file / pause / resume / remove
    state.py             list_torrents -> TorrentSnapshot DTOs
    persistence.py       restore torrents on startup
    resume.py            fast-resume file read/write
    watch.py             watch-folder discovery
    dto.py               TorrentSnapshot, NetworkStats

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
    autostart.py         launch at login
    single_instance.py   single-instance guard and CLI handoff
    updater.py           GitHub Releases update check

  web/                   HTML/CSS/JS for the embedded UI, built from partials/
  resources/             app icon and its generator
  vendor/torrent_api_py/ upstream scrapers, untouched
```

Classes are reserved for things Python's frameworks require (PyQt subclasses,
SQLAlchemy ORM, the one libtorrent `Session` dataclass). Everything else is a
module-level function, with enums for fixed value sets and frozen dataclass DTOs
for structured data.
