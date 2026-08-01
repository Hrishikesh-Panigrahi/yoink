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

- [ ] **Play video in the app.** Nothing plays media today. `openPath` hands
      the file to the OS default handler and that is the whole story.

      Playing a *finished* file in-app is barely worth the code, since
      double-clicking already does it. The version that earns its keep is
      playing *while it downloads*, which needs three things, none of them
      started:

      - sequential piece ordering and `set_piece_deadline`, so the front of the
        file lands first. libtorrent supports both and neither is used
        anywhere in `src/torrents/`.
      - a player that copes with a file growing underneath it.
      - somewhere to put a "play now" control, appearing once enough of the
        head is in.

      Codecs are the hard part, not the plumbing. QtMultimedia goes through
      Media Foundation on Windows, which is patchy on the MKV, HEVC and AC3
      combinations torrents actually ship, and HEVC wants a paid codec from the
      Store. HTML5 `<video>` in the web view is worse, because Qt's Chromium
      normally ships without proprietary codecs. Embedding libVLC through
      `python-vlc` plays essentially everything, but bolts a large native
      dependency onto a build that is currently one self-contained exe. That
      tradeoff is the actual decision here.

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

- [ ] **No linter.** CI runs `pytest` and nothing else. Ruff would catch the
      obvious things cheaply.
- [ ] **Test coverage is uneven.** Eight test modules cover search, ranking,
      safety, paths, the torrent manager and the updater. The bridge slots and
      the workers have none, which is where most of the recent code went.
