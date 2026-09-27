# Yoink

> Just yoink it from the swarm.

Yoink is a torrent client for Windows. You can search public torrent sites,
download with libtorrent, and start watching a video before it has finished
downloading. The window is PyQt6 and the interface inside it is plain
HTML, CSS and JavaScript.

There are no ready-made downloads. You run Yoink from source, or build your own
exe on your machine. Both are covered below.

- [Features](docs/FEATURES.md): what Yoink can do and how the video player works
- [Development](docs/DEVELOPMENT.md): tests, linting, building an exe, where the code lives
- [TODO](TODO.md): known bugs and things still to do

## How to run

You need Windows 10 or 11 (64-bit) and Python 3.10 or newer.

```powershell
git clone https://github.com/Hrishikesh-Panigrahi/yoink.git
cd yoink
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:PYTHONPATH = "$PWD;$PWD\src"
python src\main.py
```

Add `--minimized` if you want it to start in the tray. If you have GNU Make,
`make install` and then `make run` do the same thing.

Yoink keeps your library, settings and logs in `%LOCALAPPDATA%\Yoink\`. If you
just want to try it out without touching that, point `TORRENT_DB_PATH` at a
different file first:

```powershell
$env:TORRENT_DB_PATH = "$env:TEMP\yoink-dev.db"
```

The video player needs VLC. Either install VLC, or if you don't have admin
rights, unzip the [portable version](https://www.videolan.org/vlc/download-windows.html)
into `%LOCALAPPDATA%\Yoink\vlc`. Without VLC the rest of the app works fine,
you just won't see a Play button.

If you'd rather have an exe, run `python build.py`. You'll get `dist/Yoink.exe`,
and an installer too if Inno Setup is installed. The details are in
[Development](docs/DEVELOPMENT.md#build-an-exe-and-installer).

## Sources and DNS

A normal search ("All my enabled sites") goes to The Pirate Bay's API and to
the sites turned on in Settings > Sources. Those are 1337x, Nyaa and
YourBittorrent by default, and you can also turn on The Pirate Bay's own site
and libgen (books). "Stable APIs only" in the source filter skips the sites and
only asks The Pirate Bay's API, which is the fastest.

The Category filter works with all of them. The Pirate Bay and 1337x can be
asked for a category directly. For the others, Yoink looks at the category the
site puts on each result, or failing that the title (`S01E02` means TV,
`FitGirl` or `Repack` means a game, and so on), and leaves out what doesn't fit.

Sources that had stopped working for everyone, such as YTS, TorrentGalaxy,
KickAss and MagnetDL, have been removed.

Some internet providers answer DNS lookups for torrent sites with a fake
address, so every site looks like it's down. To get around that, Yoink looks up
site addresses over DNS-over-HTTPS (Cloudflare first, then Google). On one
connection like that, it took the number of working sources from 2 to 11. You
can switch it off in Settings > Library & app behavior if you'd rather use your
normal DNS.

It does this by replacing `socket.getaddrinfo` (see
[`src/utils/resolver.py`](src/utils/resolver.py)). Swapping hostnames for raw IP
addresses in the URLs would have been simpler, but it breaks HTTPS: the
certificate check, SNI and the `Host` header all need the real hostname.

DNS doesn't fix everything. Some providers also block sites by name when the
secure connection starts, which is what happens to 1337x, Nyaa and
YourBittorrent in India. For that you need a VPN or a proxy. Sites behind
DDoS-Guard or Cloudflare can also send back a challenge page instead of
results; the Torznab idea in [TODO.md](TODO.md) is about that.

## Using a proxy

Put a proxy in Settings > Advanced (`http://host:port`, or just `host:port`)
and press Save. From then on every search goes through it, including the
multi-site scrapers and TMDB. Torrent downloads themselves don't, and neither
do the DNS-over-HTTPS lookups. Only `http://` and `https://` proxies work for
now; SOCKS would need an extra package. Clear the box and save to go back to a
direct connection.

If you don't have a proxy, public lists on GitHub such as
[proxifly/free-proxy-list](https://github.com/proxifly/free-proxy-list),
[TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List) and
[monosans/proxy-list](https://github.com/monosans/proxy-list) are refreshed
every few hours. Expect most of them not to work: in one test only 11 of 400
answered at all, they took several seconds per search, and they tend to
disappear within a day. The ones that worked got Nyaa past the block, but
1337x (on Cloudflare) refuses them. A free proxy can see which sites you
search but not the pages themselves, since those are HTTPS. A VPN is the more
reliable option.

## Legal note

Yoink is a torrent client. It doesn't host, bundle or endorse copyrighted
content. It's up to you to use torrents and magnet links legally where you live.
