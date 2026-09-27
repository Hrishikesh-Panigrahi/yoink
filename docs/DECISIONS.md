# Decisions

Why some things are the way they are, newest first. Add to this when you make
a choice someone might later want to undo.

## Removed search sources (September 2026)

Every source was tested from an Indian connection and from outside India.
These failed from both, so they were removed:

| Source | What happened |
| --- | --- |
| YTS (the API and the scraper) | `yts.mx` no longer resolves |
| TorrentGalaxy | `torrentgalaxy.to` no longer resolves |
| TorrentProject | `torrentproject2.com` no longer resolves |
| MagnetDL | Cloudflare can't reach the site (HTTP 522) |
| Zooqle | The site returns an error (HTTP 520) |
| Torlock, LimeTorrents, GloDLS | The connection is cut from both networks |
| KickAss | Only a Cloudflare challenge page comes back |
| Bitsearch | Moved to `bitsearch.eu`, and the scraper finds nothing |
| TorrentFunk | The page loads, but the scraper finds nothing |

`cloudscraper` went too, since the MagnetDL scraper was the only thing using
it.

1337x, Nyaa, YourBittorrent and libgen were kept. Indian providers block them,
but they work from other networks, over a VPN, or through a proxy (Nyaa gets
through the free ones that **Find a free proxy** picks, 1337x doesn't).

## The proxy works through environment variables (September 2026)

Saving a proxy sets `HTTP_PROXY` and `HTTPS_PROXY` for the whole app instead of
passing a proxy to every request. `requests` reads them by default, and the
vendored scrapers' `aiohttp` sessions read them because they're created with
`trust_env=True`. That covers every search path without touching each call.

- DNS-over-HTTPS lookups skip the proxy on purpose. With a proxy given by
  hostname, looking up the proxy would otherwise need the proxy.
- SOCKS isn't supported, because both `requests` and `aiohttp` need an extra
  package for it and the app shouldn't grow a dependency just for that.
- Clearing the proxy puts back whatever proxy variables were set before Yoink
  started, so a system-wide proxy isn't lost.

In one test of the free lists, 11 of 400 proxies answered at all, 4 of those
got Nyaa past the block, and 1337x refused all of them. That's why **Find a
free proxy** tests many at once and checks each one against Nyaa.

## How the Category filter decides (September 2026)

A site that can filter by category is asked to: The Pirate Bay's API takes a
list of its category numbers, and 1337x has category search. For the rest,
each result is judged by the category label the site gives it, and failing
that by strong hints in the title (`S01E02`, `FitGirl`, `EPUB` and so on).
Results that give nothing to go on are kept, since dropping them would hide
real matches from sites that don't label anything.

"All my enabled sites" also searches The Pirate Bay's API every time instead
of only when the scrapers find nothing. Otherwise a handful of unlabelled
scraper rows could stop the API's full, filtered results from showing up.

## DNS over HTTPS by replacing getaddrinfo (August 2026)

Some Indian providers answer DNS lookups for torrent sites with a wrong
address. On one such connection, looking sites up over DNS-over-HTTPS took the
number of reachable sources from 2 to 11.

The lookup is done by replacing `socket.getaddrinfo`, so every library gets
the right address without knowing about it. Rewriting URLs to use raw IP
addresses would have been simpler, but it breaks HTTPS: the certificate check,
SNI and the `Host` header all need the real hostname.

## Playing a file while it downloads (August 2026)

- **The end of the file is fetched early, not just the start.** MP4 files
  usually keep their index (`moov`) at the end and MKV files keep their seek
  points there. Without it the player can't show the length or skip ahead.
- **VLC is fed through callbacks.** VLC normally treats the last byte on disk
  as the end, so a file that's 25% downloaded plays for 25% and stops. With
  `libvlc_media_new_callbacks` (`src/player/source.py`), a read waits for
  missing data instead, and VLC is told the file's full size up front.
- **libVLC instead of QtMultimedia.** On Windows QtMultimedia uses Media
  Foundation, which struggles with the MKV, HEVC and AC3 files common on
  torrent sites. The cost is about 40 to 50 MB of VLC in the build.
