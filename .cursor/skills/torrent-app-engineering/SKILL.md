---
name: torrent-app-engineering
description: Engineering guidance for Yoink, a PyQt6 + libtorrent Windows desktop torrent client with an HTML/JS UI in QWebEngine. Use this whenever working in this repository on torrent logic, SQLite persistence, the web UI or the bridge, search providers, the in-app player, tests, or building the Windows exe/installer — including refactors, bug fixes, new features, code review, or "make this feel more polished" style requests. Trigger even if the user doesn't say "Yoink" by name but is clearly working in this codebase (mentions libtorrent, the bridge, QWebChannel, main.js, yoink.db, build.py, etc.).
---

# Yoink Engineering

Yoink is a PyQt6 shell hosting a `QWebEngineView`: the UI is HTML/CSS/JS in `src/web/`, the Python side is exposed to it as a `bridge` object over `QWebChannel`, and torrents run on libtorrent with SQLite persistence. This skill captures how to work safely and consistently in this codebase — read it before touching code, not just before shipping.

## Before you start

1. Skim `.cursor/rules/*.mdc` — these hold conventions that override generic Python/Qt habits.
2. Identify which layer owns the change:
   - `torrents/` — libtorrent session, actions, state, streaming order
   - `search/` and `providers/` — querying sources, ranking, safety flags
   - `db.py` / `models.py` — SQLite settings and saved torrents
   - `bridge/` and `workers.py` — the slots JS calls, and the threads behind them
   - `src/web/` — everything the user sees
   - `player/` — libvlc playback
   - `utils/` — stateless helpers

   Most bugs and features live cleanly in one layer. If a change seems to span three, that's a signal the abstraction is wrong, not that the task is big.
3. Set up the environment: Windows, `.venv`, `pip install -r requirements.txt`, `PYTHONPATH=$PWD;$PWD/src`.
4. Never touch the real library at `%LOCALAPPDATA%\Yoink\yoink.db` during dev work. Set `TORRENT_DB_PATH` to a temp file before launching the app; the test suite already does this in `tests/conftest.py`.

## Making a change

The goal is a change that reads as an intentional decision, not a patch bolted onto whatever was already there.

1. **Start from the user-facing behavior**, not the code. What is someone doing in the app when this matters — searching, adding a torrent, monitoring progress, pausing/resuming, picking files, playing a video, setting a download folder, removing an item?
2. **Write or update a test before restructuring.** If torrent or search logic can't be tested without booting the GUI, that's the actual problem to fix, not a reason to skip the test.
3. **Make the smallest change that improves the specific thing you're fixing.** Resist the urge to also "clean up" adjacent code in the same commit — separate concerns, separate diffs.
4. Run `python -m pytest` and `python -m ruff check .` from the venv before considering the change done.

## UI work

Treat the UI as a set of named states, not one handler accumulating branches.

- Edit `src/web/partials/` or `index.template.html`, never the generated `index.html`, then run `python build.py --compose-html`.
- Every interactive flow needs: an empty state, a progress/in-flight state, an error state, and — for anything destructive (remove torrent, clear data) — a confirmation step. If you're only implementing the happy path, say so explicitly rather than silently skipping the others.
- Long-running work (adding a torrent, searching, fetching metadata, buffering a stream) must never block the Qt main thread. The slot starts a worker and returns; the result comes back as a bridge signal.
- The UI should be usable by someone who doesn't know what a "tracker" or "peer" is. If a label or error message requires torrent-domain knowledge to parse, rewrite it in plain terms.
- Verify UI changes in the running app, not just by reading the diff. The run-app skill in `.claude/skills/run-app/` covers launching, screenshotting and driving the page over DevTools.

## Building the Windows exe

There are no published releases; people build their own.

1. Confirm all dependencies — especially `libtorrent` — install cleanly in the venv before touching packaging.
2. Runtime paths (logs, `yoink.db`, fast-resume data, downloads) must resolve to user-writable locations, not the install directory.
3. `python build.py` runs PyInstaller with resources and hidden imports listed explicitly, bundles a VLC runtime (or fails, unless `--no-player`), and builds the Inno Setup installer when `ISCC` is available.
4. Smoke-test the built exe on a clean Windows profile (not just the dev machine) — missing DLLs and path assumptions only show up there.
5. The build is unsigned and SmartScreen will warn on first run; don't hide that from users.

## Quick sanity check before calling something done

- Would this logic still make sense to someone reading it without you in the room?
- Can the change be tested with `pytest` alone, no Qt event loop running?
- Does the UI tell a non-technical user what's happening, without requiring them to understand torrenting?
- Does `python build.py` still work from a clean checkout, not just your dev environment with cached state?
