# TODO

Known work, roughly in the order it matters. Nothing here is in progress.

## Before the site is public

- [ ] **Turn on GitHub Pages.** Settings → Pages, source *Deploy from a branch*,
      branch `main`, folder `/docs`. The page is written and committed. Skip
      this if it is already switched on.

      The stable `Yoink-Setup.exe` alias does now exist: `v2.0.1` was tagged
      after the workflow step that creates it, so the download button's no-JS
      fallback resolves.
- [ ] **Tag `v2.0.2` to break the update loop.** `v2.0.1` was tagged without
      bumping `src/version.py`, so the workflow built and published
      `Yoink-Setup-2.0.0.exe` under a `v2.0.1` release. The updater compares the
      newest tag against `__version__`, so an installed copy reports 2.0.0,
      is told 2.0.1 is available, installs it, still reports 2.0.0, and is told
      again. Every user sits in that loop forever.

      `src/version.py` is now bumped to `2.0.2`. Nothing is published until a
      tag is pushed, so the fix is one command:
      `git tag v2.0.2 && git push origin v2.0.2`. Until then the app reports a
      version higher than the newest release, which offers no update at all.
      That is wrong but harmless, unlike the loop.

      Re-tagging `v2.0.1` would be worse, since it is already published.

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
