---
name: torrent-app-engineering
description: How to work on Yoink, a PyQt6 + libtorrent torrent client for Windows whose interface is HTML/JS running in QWebEngine. Use this whenever working in this repository on torrent logic, the SQLite database, the web UI or the bridge, search sources, the video player, tests, or building the exe and installer. That includes refactors, bug fixes, new features, code review and "make this feel more polished" requests. Use it even if the user doesn't say "Yoink" but is clearly working in this codebase (they mention libtorrent, the bridge, QWebChannel, main.js, yoink.db, build.py and so on).
---

# Working on Yoink

Yoink is a PyQt6 window holding a `QWebEngineView`. The interface is HTML, CSS
and JavaScript in `src/web/`. The Python side is available to the page as a
`bridge` object over `QWebChannel`, and torrents run on libtorrent with a
SQLite database. Read this before changing code, not just before shipping.

## Before you start

1. Skim `.cursor/rules/*.mdc`. The conventions there win over general Python
   and Qt habits.
2. Work out which part of the code owns the change:
   - `torrents/`: the libtorrent session, actions, state, streaming order
   - `search/` and `providers/`: querying sources, ranking, safety warnings
   - `db.py` and `models.py`: settings and saved torrents in SQLite
   - `bridge/` and `workers.py`: what the page can call, and the threads behind it
   - `src/web/`: everything the user sees
   - `player/`: video playback with libVLC
   - `utils/`: small shared helpers

   Most bugs and features sit in one of these. If a change seems to touch three
   of them, the design is probably wrong rather than the task being big.
3. Set up: Windows, a `.venv`, `pip install -r requirements.txt`, and
   `PYTHONPATH=$PWD;$PWD/src`.
4. Never touch the real library at `%LOCALAPPDATA%\Yoink\yoink.db` while
   developing. Set `TORRENT_DB_PATH` to a temporary file before starting the
   app. The tests already do this in `tests/conftest.py`.

## Making a change

Aim for a change that looks like it was meant to be there, not a patch added on
top of whatever was already there.

1. **Start from what the user is doing**, not from the code. Are they
   searching, adding a torrent, watching progress, pausing, picking files,
   playing a video, choosing a folder, or removing something?
2. **Write or update a test before restructuring.** If torrent or search logic
   can't be tested without starting the GUI, fix that instead of skipping the
   test.
3. **Make the smallest change that fixes the thing you're working on.** Don't
   tidy up the code around it in the same commit. Separate changes, separate
   diffs.
4. **Let the code explain itself.** Choose clear names and small functions
   instead of explanatory comments. Only write a comment when the reason for
   something isn't obvious from the code (a library quirk, a workaround, an
   ordering that matters), and keep it to a sentence or two.
5. Run `python -m pytest` and `python -m ruff check .` in the venv before you
   call it done.

## UI work

Think of the UI as a set of named states rather than one handler that keeps
growing.

- Edit `src/web/partials/` or `index.template.html`, never the generated
  `index.html`, and then run `python build.py --compose-html`.
- Each feature has its own module in `src/web/js/`, with a `bind...Events()`
  function for its buttons and a `connect...Signals()` function for bridge
  signals. `main.js` only calls them in order. Put new code in the module it
  belongs to.
- Every flow needs an empty state, a loading state and an error state. Anything
  destructive (removing a torrent, clearing data) also needs a confirmation. If
  you only build the happy path, say so.
- Slow work (adding a torrent, searching, fetching metadata, buffering a
  stream) must never block the Qt main thread. The slot starts a worker and
  returns straight away, and the result comes back as a bridge signal.
- Someone who doesn't know what a "tracker" or a "peer" is should still be able
  to use the app. If a label or an error needs torrent knowledge to make sense,
  reword it.
- Check UI changes in the running app, not only in the diff. The run-app skill
  in `.claude/skills/run-app/` explains how to start the app, take screenshots
  and drive the page over DevTools.

## Building the Windows exe

There are no published releases, so people build their own.

1. Make sure every dependency, especially `libtorrent`, installs cleanly in the
   venv before changing anything about packaging.
2. Logs, `yoink.db`, fast-resume data and downloads must go to folders the user
   can write to, never the install folder.
3. `python build.py` runs PyInstaller with the resources and hidden imports
   listed explicitly, includes VLC (or stops with an error, unless you pass
   `--no-player`), and builds the Inno Setup installer when `ISCC` is available.
4. Try the built exe on a clean Windows user profile, not just your own.
   Missing DLLs and wrong paths only show up there.
5. The build isn't signed, so SmartScreen warns on first run. Tell users that
   rather than hiding it.

## Before you call it done

- Would the code still make sense to someone reading it without you there?
- Can the change be tested with `pytest` alone, without a Qt event loop?
- Does the UI tell a non-technical user what's going on, without them needing
  to understand torrents?
- Does `python build.py` still work from a clean checkout, not just in your own
  environment?
