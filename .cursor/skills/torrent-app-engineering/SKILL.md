---
name: torrent-app-engineering
description: Improve, refactor, test, redesign, or package the Torrent App Python desktop client. Use when working on code quality, PyQt6 UI/UX, libtorrent behavior, SQLite persistence, tests, or Windows app distribution for this repository.
---

# Torrent App Engineering

## First Steps

1. Read the relevant `.cursor/rules/*.mdc` files before changing code.
2. Confirm the work area: core torrent behavior, database persistence, PyQt UI, search providers, tests, or packaging.
3. Run from Windows with `.venv`, Python 3.11, and `PYTHONPATH=$PWD;$PWD/src`.
4. Protect the real `torrent.db`; tests should use `TORRENT_DB_PATH` or a temporary database.

## Refactoring Workflow

1. Find the user-facing behavior first.
2. Identify the owning layer: `gui`, `core`, `database`, or `utils`.
3. Make the smallest behavior-preserving cleanup that improves readability.
4. Add or update focused tests before broad rewrites.
5. Run `python -m pytest tests` from the virtual environment.

## UI Improvement Workflow

1. Start from user jobs: search, add, monitor, pause/resume, choose files, set folder, remove.
2. Sketch the desired interaction before changing widgets.
3. Keep long-running work off the main Qt thread.
4. Add clear empty states, progress states, error states, and destructive confirmations.
5. Prefer reusable panels/widgets over growing `MainWindow`.

## Windows App Workflow

1. Verify dependencies install on Python 3.11, especially `libtorrent`.
2. Make runtime paths user-writable for logs, database, settings, and downloads.
3. Build with PyInstaller using explicit resources and hidden imports.
4. Smoke test on a clean Windows profile.
5. If distributing broadly, wrap the build in an installer and consider code signing.

## Quality Bar

- Code should read as a set of named decisions, not a pile of event handlers.
- Core logic must be testable without opening a GUI.
- UI should explain what is happening without requiring torrent knowledge.
- Packaging should not depend on the development checkout.
