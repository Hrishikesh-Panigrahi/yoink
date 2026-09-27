# TODO

Things still to do, most important first. Nobody is working on any of these
right now. Finished items get deleted rather than ticked off, since git history
already has them.

## Search

Public torrent sites keep changing their addresses, their pages and their bot
protection. That's why the multi-site scrapers break so often, and why the
source health check exists.

- [ ] **Most multi-site scrapers are blocked here.** 1337x, Nyaa and
      YourBittorrent work from other networks, but Indian providers cut the
      connection during the HTTPS handshake, and libgen.is doesn't answer. DNS
      is fine at that point, so DNS-over-HTTPS can't help: the block is on the
      site's name. Only The Pirate Bay (its API and its scraper) gets through.
      A VPN fixes it, and so would the proxy setting once it does something
      (see below). The lasting fix is one of the two options further down.
- [ ] **Say when every source failed.** Right now a search where every source
      errored looks exactly like a search with no matches. We already collect
      the health data, so the empty results screen could show it.

Two longer-term options, neither started:

- [ ] **Torznab.** [Jackett](https://github.com/Jackett/Jackett) and
      [Prowlarr](https://github.com/Prowlarr/Prowlarr) offer one standard API
      for more than 500 sites and keep their own scrapers up to date, so a site
      changing its layout would stop being our problem. The catch is that the
      user has to run one of them in the background, which is a lot to ask of
      a desktop app that currently needs nothing else.
- [ ] **Bitmagnet.** [bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet)
      finds torrents on the DHT network itself and offers a GraphQL API, so
      there's no scraping at all. Same catch: it has to run in the background.

## Known bugs

Worst first.

- [ ] **One stray click can delete a torrent.** *Remove* in the ⋮ menu acts
      straight away, and the bin button deletes on a second click within 3
      seconds, which is easy to do by accident. There's no undo. A real torrent
      was lost this way during development and only came back because SQLite
      doesn't wipe deleted rows straight away
      (`.claude/skills/run-app/scripts/recover_torrents.py`).

      The simplest proper fix: keep removed torrents in a `removed` table for a
      few days and put an Undo button in the toast.

- [ ] **The proxy setting does nothing.** Settings > Advanced saves a proxy URL
      and a user agent, but no search code ever reads them. `setProxy` in
      `bridge/settings_slots.py` tries to import `providers._http`, which
      doesn't exist, and quietly ignores the error. Either route the providers'
      `requests` calls through the saved proxy and user agent, or hide the
      setting until that's done.

- [ ] **One `.text-input` rule changes every input.** The onboarding styles in
      `css/modals.css` include a `.text-input` rule that isn't limited to the
      onboarding modal. It overrides the padding, background and corner radius
      from `base.css` on every text box in the app, and it's what once made the
      search icon sit on top of the first letter you typed. Limiting it to
      `.modal-wizard` is the fix, but that visibly changes the settings and
      search boxes, so each screen needs checking afterwards.
      `scripts/audit_layout.js` in the run-app skill helps with that.

- [ ] **Skipping ahead past what's downloaded freezes for 30 seconds, then
      stops.** `GrowingFile` waits `STALL_TIMEOUT_SECONDS` for data that the
      in-order download won't reach until later, then gives up. That's how it
      was designed, but it's a bad experience. Moving the piece deadlines to
      the point you skipped to (`set_piece_deadline`) would fix it.

## Player

- [ ] **Polish.** There's no fullscreen, no keyboard shortcuts, and the volume
      goes back to 80 every time. The window is meant to be simple, but these
      three make it feel unfinished.
- [ ] **Test HEVC and AC3.** Those formats are the reason we chose VLC over
      QtMultimedia, and neither has actually been tried. H.264 video with MP3
      audio works end to end with a real local swarm.

## Housekeeping

- [ ] **Tests.** `main_window.py` and the JavaScript in `src/web/` have none.
