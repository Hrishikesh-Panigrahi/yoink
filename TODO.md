# TODO

Known work, roughly in the order it matters. Nothing here is in progress.
Finished items are removed rather than ticked; git history has them.

## Search back end

Public torrent sites change domains, markup and bot protection constantly,
which is why the vendored providers behind `ProviderMode.MULTI` are flaky and
why the health check exists at all.

- [ ] **The vendored scrapers return nothing.** This is the real remaining gap
      and DNS-over-HTTPS does not touch it. With DoH on, all four sampled sites
      connect and all four return zero rows:

      - `1337x.to` resets the connection mid-handshake. DNS is correct by then,
        so this is blocking on the TLS SNI, which nothing inside the process can
        route around. The proxy setting in Settings, or a VPN, is the answer.
      - `nyaa.si` answers HTTP 200 from `ddos-guard` — an interstitial, not
        results, so there is nothing to parse.

      `cloudscraper` is already a dependency but only `src/vendor/`'s
      `magnet_dl` uses it. Wiring it into the other adapters is the cheapest
      experiment with the largest possible payoff; fixing it properly is one of
      the two items below.
- [ ] **Say when every provider failed.** A search where all providers error
      looks identical to one that genuinely has no matches. The health data is
      already collected; surface it on the empty state.

Two durable ways out, neither started:

- [ ] **Torznab.** [Jackett](https://github.com/Jackett/Jackett) and
      [Prowlarr](https://github.com/Prowlarr/Prowlarr) expose one standard
      endpoint across 500+ indexers and update their own scrapers, so a site
      changing its HTML stops being our problem. The cost is that the user has
      to run a local daemon, which is a real ask for a desktop app that
      currently needs nothing.
- [ ] **Bitmagnet.** [bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet)
      crawls the DHT directly and exposes GraphQL, so there is no scraping at
      all. Same daemon problem.

## Known bugs, found but not fixed

Ordered by how much damage each can do.

- [ ] **Remove is one stray click from destroying a torrent.** The kebab's
      *Remove* fires immediately, and *Cancel* arms on the first click and
      deletes on the second within 3 seconds — easy to trigger by accident and
      there is no undo. A real torrent was lost this way during development. It
      was recoverable only because SQLite leaves deleted rows in the file's free
      pages (`.claude/skills/run-app/scripts/recover_torrents.py`).

      Cheapest real fix: keep removed torrents in a `removed` table for a few
      days and offer "undo" in the toast.

- [ ] **The CSS module split is half-done.** `styles.css` `@import`s seven files
      from `css/`, but `settings.css` is 40 KB and holds rules for the modals,
      the details view and a second, unscoped `.text-input` — which is what put
      the search icon on top of the first character, since it is imported last
      and won on order alone. Move the non-settings rules into the file they
      belong to. `scripts/audit_layout.js` in the run-app skill will catch the
      regressions.

- [ ] **Seeking past the buffered region stalls for 30s, then stops.**
      `GrowingFile` waits `STALL_TIMEOUT_SECONDS` for bytes that sequential
      order will not fetch until it gets there, then reports end-of-stream.
      Correct given the design, but a poor experience. Re-issuing
      `set_piece_deadline` around the seek target would make it work properly.

## Player

- [ ] **Player polish.** No fullscreen, no keyboard shortcuts, and the volume
      resets to 80 every time. The window is deliberately minimal, but those
      three are what makes it feel unfinished.
- [ ] **Verify HEVC and AC3.** They are the reason libVLC was chosen over
      QtMultimedia and neither has actually been played. H.264 with MP3 audio is
      confirmed working end to end against a real local swarm.

## Housekeeping

- [ ] **Test coverage.** `main_window.py` and the `src/web/` JS have no tests.
