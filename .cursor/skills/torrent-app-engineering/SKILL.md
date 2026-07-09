---
name: torrent-app-engineering
description: Engineering guidance for Yoink, a PyQt6 + libtorrent Windows desktop torrent client. Use this whenever working in this repository on core torrent logic, SQLite persistence, PyQt6 UI/UX, search providers, tests, or Windows packaging/distribution — including refactors, bug fixes, new features, code review, or "make this feel more polished" style requests. Trigger even if the user doesn't say "Yoink" by name but is clearly working in this codebase (mentions libtorrent, MainWindow, torrent.db, PyInstaller build for this app, etc.).
---

# Yoink Engineering

Yoink is a PyQt6 desktop app wrapping libtorrent, with SQLite persistence. This skill captures how to work safely and consistently in this codebase — read it before touching code, not just before shipping.

## Before you start

1. Skim `.cursor/rules/*.mdc` — these hold conventions that override generic Python/Qt habits.
2. Identify which layer owns the change: `core` (torrent/session logic), `database` (SQLite), `gui` (PyQt6), or `utils`. Most bugs and features live cleanly in one layer — if a change seems to span three layers, that's a signal the abstraction is wrong, not that the task is big.
3. Set up the environment: Windows, `.venv`, Python 3.11, `PYTHONPATH=$PWD;$PWD/src`.
4. Never touch the real `torrent.db` during dev/test work. Point at `TORRENT_DB_PATH` or a temp file — a corrupted local DB is a bad way to lose an afternoon.

## Making a change

The goal is a change that reads as an intentional decision, not a patch bolted onto whatever was already there.

1. **Start from the user-facing behavior**, not the code. What is someone doing in the app when this matters — searching, adding a torrent, monitoring progress, pausing/resuming, picking files, setting a download folder, removing an item?
2. **Write or update a test before restructuring.** If `core` logic can't be tested without booting the GUI, that's the actual problem to fix, not a reason to skip the test.
3. **Make the smallest change that improves the specific thing you're fixing.** Resist the urge to also "clean up" adjacent code in the same commit — separate concerns, separate diffs.
4. Run `python -m pytest tests` from the venv before considering the change done.

## UI work

Treat the UI as a set of named states, not a single `MainWindow` accumulating handlers.

- Every interactive flow needs: an empty state, a progress/in-flight state, an error state, and — for anything destructive (remove torrent, clear data) — a confirmation step. If you're only implementing the happy path, say so explicitly rather than silently skipping the others.
- Long-running work (adding a torrent, searching, hashing) must never block the Qt main thread. If you're not sure whether an operation is long-running, assume it is.
- The UI should be usable by someone who doesn't know what a "tracker" or "peer" is. If a label or error message requires torrent-domain knowledge to parse, rewrite it in plain terms.
- Prefer extracting a reusable panel/widget over adding another branch to `MainWindow`. If `MainWindow` grew this change, ask whether the new logic actually belongs in its own widget.

## Windows packaging & distribution

1. Confirm all dependencies — especially `libtorrent` — install cleanly on Python 3.11 before touching packaging.
2. Runtime paths (logs, `torrent.db`, settings, downloads) must resolve to user-writable locations, not the install directory.
3. Build with PyInstaller, listing resources and hidden imports explicitly rather than relying on auto-detection.
4. Smoke-test the built .exe on a clean Windows profile (not just the dev machine) — missing DLLs and path assumptions only show up there.
5. For broader distribution, wrap the PyInstaller output in an installer and consider code signing; an unsigned standalone .exe will trip SmartScreen for most users.

## Quick sanity check before calling something done

- Would this logic still make sense to someone reading it without you in the room?
- Can the `core` change be tested with `pytest` alone, no Qt event loop running?
- Does the UI tell a non-technical user what's happening, without requiring them to understand torrenting?
- Does packaging work from a clean checkout, not just your dev environment with cached state?