# TODO

Known work, roughly in the order it matters. Nothing here is in progress.

## Before the site is public

- [ ] **Turn on GitHub Pages.** Settings → Pages, source *Deploy from a branch*,
      branch `main`, folder `/docs`. The page is written and committed. Skip
      this if it is already switched on.

      The stable `Yoink-Setup.exe` alias does now exist: `v2.0.1` was tagged
      after the workflow step that creates it, so the download button's no-JS
      fallback resolves.
- [x] **Broke the update loop.** `v2.0.1` was tagged without bumping
      `src/version.py`, so the workflow built `Yoink-Setup-2.0.0.exe` and
      published it as the `v2.0.1` release. The updater compares the newest tag
      against `__version__`, so an installed copy reported 2.0.0, was offered
      2.0.1, installed it, still reported 2.0.0, and was offered it again.
      Fixed by bumping to `2.0.2` and tagging that.

      Worth remembering: **bump `src/version.py` in the same commit you tag.**
      Tagging without it publishes a release whose binary disagrees with the
      tag, and the updater has no way to tell.

## Distribution

- [ ] **Code signing.** Yoink is unsigned, so SmartScreen warns on first run.
      The download page explains this rather than hiding it, which is the right
      short-term answer, but a certificate would remove the friction entirely.
      When one is available, sign before the workflow's "Add stable-named
      installer alias" step, or the alias becomes a copy of the unsigned build,
      and regenerate `SHA256SUMS.txt` afterwards.
- [ ] **Android.** Nothing in this repo builds an APK. This is a second product
      rather than another build target: PyQt6 does not run on Android and
      Buildozer only covers Kivy, so it means a Kotlin UI over `libtorrent4j`,
      or Flutter with a native torrent layer. None of the Python carries over
      except the search and ranking logic, which would have to be reimplemented
      from `src/search/`. Play Store allows torrent clients but scrutinises
      them, so plan for a sideloaded APK or F-Droid. The landing page already
      shows an Android button automatically once a release contains a `.apk`,
      so no site work is needed when one appears.
- [ ] **Real screenshots.** The landing page uses a hand-written mock of the
      interface, labelled as a mock. Actual screenshots of the running app
      would be more convincing and more honest.

## Features

- [x] **Play video in the app.** A **Play** button on any download whose
      torrent holds a video opens it in an in-app window while it is still
      downloading. All three pieces are in:

      - **Piece ordering.** `src/torrents/streaming.py` sets libtorrent's
        `sequential_download` flag and deadlines the head *and* the tail. The
        tail matters because MP4 keeps `moov` at the end unless written for
        streaming and Matroska keeps its cues there, so a player that cannot
        see the tail reports an unknown duration and refuses to seek.
      - **The player.** libVLC through `python-vlc`, in `src/player/`.
      - **The control.** `.dl-play` on the download row, shown only when a
        runtime exists and `getPlayableFile` finds a video.

      **The codec decision was libVLC**, and the cost was accepted knowingly:
      roughly 40-50 MB of plugin tree in the installer, and the build is no
      longer one self-contained exe in the strict sense. QtMultimedia was
      rejected because Media Foundation is patchy on exactly the MKV, HEVC and
      AC3 mix torrents ship — a player that fails on half the library is worse
      than no player.

      `python-vlc` is only a ctypes binding, and `import vlc` *raises* when no
      runtime is present, so it is never imported at module scope. Everything
      goes through `player.runtime.load_vlc()`, which returns a reason instead.
      Discovery order: `YOINK_VLC_DIR`, the copy bundled beside a frozen build,
      a portable copy under `%LOCALAPPDATA%\Yoink\vlc`, then an installed VLC
      via registry and Program Files. With none of them the app runs normally
      and the button stays hidden. `build.py` fails rather than shipping a dead
      button; `--no-player` opts out.

      Verified against real libvlc 3.0.23: runtime discovery, H.264 decode and
      rendering into the Qt surface, the audio clock, playing a file that grows
      underneath the player, and closing the window mid-stream without hanging.

      Three things that verification caught, all fixed:

      - Setting `VLC_PLUGIN_PATH` and calling `add_dll_directory` is *not*
        enough. python-vlc's own loader reads `PYTHON_VLC_LIB_PATH` and
        `PYTHON_VLC_MODULE_PATH`, and without them falls back to
        `CDLL(".\\libvlc.dll")` — a relative path resolved against the working
        directory, so it looked for the library in the repo root.
      - python-vlc calls `sys.exit(1)` instead of raising when the library will
        not load. `SystemExit` is a `BaseException`, so the `except Exception`
        guard would have let it through and killed the app.
      - `vlc.MediaOpenCb` and friends are exported as bare `c_void_p`
        subclasses; the real CFUNCTYPE prototypes live in a scope python-vlc
        never exports, so `vlc.MediaOpenCb(fn)` raises "cannot be converted to
        pointer". `player/source.py` declares the prototypes itself and casts.

      Still unverified: HEVC and AC3 specifically, and anything about how it
      behaves on a real swarm rather than a file being appended to on disk.

## Search back end

Public torrent sites change domains, markup and bot protection constantly,
which is why the long-tail providers behind `ProviderMode.MULTI` are flaky and
why the health check exists at all. Two ways out, neither started:

- [ ] **Torznab.** [Jackett](https://github.com/Jackett/Jackett) and
      [Prowlarr](https://github.com/Prowlarr/Prowlarr) expose one standard
      endpoint across 500+ indexers and update their own scrapers, so a site
      changing its HTML stops being our problem. The cost is that the user has
      to run a local daemon, which is a real ask for a desktop app that
      currently needs nothing.
- [ ] **Bitmagnet.** [bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet)
      crawls the DHT directly and exposes GraphQL, so there is no scraping at
      all. Same daemon problem.

Older notes on both live in `todo.txt`, which this file supersedes.

## Housekeeping

- [x] **Added a linter.** `ruff.toml` selects pycodestyle, pyflakes, import
      order, bugbear and comprehension rules at 100 columns, with `src/vendor/`
      excluded because that tree is vendored. CI runs it as its own Linux job —
      ruff is pure Python, so it does not need a Windows runner or the PyQt6 and
      libtorrent wheels — which keeps lint and test failures as separate signals.
      `make lint` runs the same check locally.

      Style modernisation (`UP`) and refactor hints (`SIM`) are deliberately
      off. Turning them on adds ~150 findings, nearly all mechanical rewrites of
      `Optional[X]` and `List[X]`; that is a rename pass, not a lint gate, and
      it should be its own commit if anyone wants it.
- [x] **Covered the bridge slots and the workers.** `tests/test_bridge_slots.py`
      and `tests/test_workers.py` add 89 tests, taking the suite from 60 to 149.

      Both avoid Qt machinery rather than mocking it. The bridge tests build the
      object with `__new__` plus a hand-run `QObject.__init__`, so no libtorrent
      session or worker threads start, then attach one shared real session and
      fake workers — every slot under test is the real implementation, and
      signals still deliver because PyQt does direct connections without a
      running `QApplication`. The worker tests call `run()` on the test thread
      instead of `start()`, so emissions arrive synchronously; the polling
      workers are stopped from inside their own signal handler to bound the
      loop to one pass.

      Still uncovered: `main.py`, `main_window.py`, and the `src/web/` JS.
