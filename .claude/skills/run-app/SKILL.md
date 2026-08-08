---
name: run-app
description: Launch and drive the Yoink desktop app (PyQt6 + QWebEngine) to verify a change in the real UI - includes screenshotting the window, driving the web layer over the DevTools protocol, and the database isolation that keeps a dev run from touching the user's real library. Use when asked to run, start, screenshot, or click through the app.
---

# Running Yoink

Yoink is a PyQt6 shell hosting a `QWebEngineView`. The Python side is the
`bridge` object exposed over `QWebChannel`; everything the user sees is HTML
in `src/web/`. That split decides how you drive it: Python state through the
app's own logs, UI state through the DevTools protocol.

## Isolate the database first

**A dev run writes to the user's real library** at
`%LOCALAPPDATA%\Yoink\yoink.db` - the same file the installed app uses. It
restores their torrents on launch, and anything you click is permanent. A
stray click on Remove in a dev run deleted a real torrent during one session.

Set `TORRENT_DB_PATH` unless you specifically mean to work on real data:

```bash
TORRENT_DB_PATH="$TEMP/yoink-dev.db"
```

The same applies to `pytest`. Most test modules set it themselves, but the
env var costs nothing and removes the question.

If something *does* get deleted, it is usually recoverable: SQLite leaves
deleted rows in the file's free pages. `scripts/recover_torrents.py` pulls
magnets and info hashes back out.

## Launch

`src/` has to be on `PYTHONPATH` - the app uses flat imports (`import db`,
`from bridge import Bridge`), not package-relative ones.

```bash
cd <repo>
python build.py --compose-html   # only needed after editing src/web/partials/
PYTHONPATH="<repo>;<repo>/src" .venv/Scripts/python.exe src/main.py
```

Run it in the background - it is a GUI app and will not return. `make run`
does the same thing plus `compose-html`, if GNU Make is installed.

Watch the startup log; it answers most "did it work" questions on its own:

```
bridge - INFO - Initializing Bridge
torrents.session - INFO - libtorrent session ready
torrents.persistence - INFO - Restored N torrent(s) from database
main_window - INFO - Loading UI from file:///.../src/web/index.html
player.runtime - INFO - Using libvlc from ... (found via data dir)
```

That last line only appears once the JS has called `getPlayerStatus`, so it
doubles as proof the web layer loaded and the bridge is answering.

## Screenshot the window

**Use `PrintWindow`, not `CopyFromScreen`.** `CopyFromScreen` copies a screen
*region*, so it captures whatever is actually on top - which, on a machine
where you cannot raise the window, is someone else's application. It captured
a user's private chat window during one session. `PrintWindow` renders the
target window's own contents and cannot capture anything else.

```bash
powershell -File .claude/skills/run-app/scripts/screenshot.ps1
```

Then **look at the image**. A black frame means QWebEngine has not painted
yet - wait a couple of seconds and retake.

Do not bother trying to raise the window first. Windows blocks foreground
stealing from a background process; `SetForegroundWindow` returns without
doing anything, even with the `AttachThreadInput` trick. `PrintWindow` does
not need the window raised, which is the other reason to prefer it.

## Drive the UI

You cannot click the app from outside: synthetic mouse input needs the window
foregrounded, and see above. Use QWebEngine's remote debugging instead - it is
the supported way in and it drives the real UI, not a copy of it.

Relaunch with the port set (it must be set before `QApplication` starts):

```bash
PYTHONPATH="<repo>;<repo>/src" QTWEBENGINE_REMOTE_DEBUGGING=9222 \
  .venv/Scripts/python.exe src/main.py
```

Then evaluate JavaScript in the page:

```bash
.venv/Scripts/python.exe .claude/skills/run-app/scripts/cdp.py expressions.json
```

`expressions.json` is a list of JS strings. The script wraps each one in a
3-second timeout, because a promise that never settles otherwise hangs the
whole run - `Runtime.evaluate` with `awaitPromise` waits forever.

Useful expressions:

```js
document.querySelector('button[data-view="downloads"]').click()   // switch view
document.querySelectorAll('#downloadsList .download-row').length  // row count
document.querySelector('#downloadRowTpl').content                 // row template
  .querySelector('.dl-play') !== null
```

Three things that will trip you up:

- **Never construct a second `QWebChannel`.** It looks like the obvious way to
  reach the bridge, and it quietly breaks the running app: the extra channel
  takes over the shared `qt.webChannelTransport`, so signals stop arriving at
  the handlers `main.js` registered. The visible symptom is a search that spins
  forever, because `searchCompleted` never lands - and it survives until the
  page is reloaded, so everything you test afterwards is wrong too. This cost a
  long debugging detour into a bug that did not exist.

  Drive the UI through the DOM instead - click the real controls and read the
  rendered result:

  ```js
  document.querySelector('#searchInput').value = 'ubuntu';
  document.querySelector('#searchForm').dispatchEvent(
    new Event('submit', {bubbles: true, cancelable: true}));
  ```

  If you truly need a bridge method with no UI path to it, restart the app
  afterwards rather than trusting the session.
- **`bridge` is not global.** `main.js` is one big IIFE, so `bridge`, `state`
  and `els` are closed over and unreachable from the console. That is the
  reason the extra-channel trick is tempting. Resist it; query the DOM.
- **Template ids do not match their class names.** The download row lives in
  `#downloadRowTpl`, not `#downloadTpl` (that is the *variable* name in
  `main.js`). Check `src/web/partials/templates.html` before guessing.

## Searches take ~20 seconds, and that is the network

Stable mode queries YTS and The Pirate Bay. On a connection that blocks torrent
hosts - common with Indian ISPs - `yts.mx` is unreachable and burns two 10s
connect timeouts before the Pirate Bay results (via `apibay.org`, usually not
blocked) come back. So a search looks hung for ~20s and then works.

Check reachability before assuming the app is broken:

```bash
python -c "import socket; socket.create_connection(('yts.mx',443),timeout=8)"
```

`apibay.org` reachable while `yts.mx`, `thepiratebay.org` and `1337x.to` all
time out is the signature of ISP blocking, not an outage.

## The in-app player

Playback needs a libvlc runtime; `python-vlc` is only a binding. Discovery
order is in `src/player/runtime.py`: `YOINK_VLC_DIR`, the copy bundled beside
a frozen build, `%LOCALAPPDATA%\Yoink\vlc`, then an installed VLC.

Installing VLC properly needs administrator rights. Unzipping VLC's official
portable build into `%LOCALAPPDATA%\Yoink\vlc` does not, and is picked up with
no configuration - that is the path to use on a machine without elevation.

With no runtime the app runs normally and the Play button stays hidden;
`getPlayerStatus` returns the reason. So a missing Play button means "no VLC"
at least as often as it means "no video in this torrent" - check
`getPlayerStatus` before debugging the UI.

Verifying playback itself needs a video file with **an audio track**. VLC's
master clock is driven by the audio output: on a video-only file, frames
render but `get_time()` stays frozen and playback runs unpaced, which looks
exactly like a bug and is not one.
