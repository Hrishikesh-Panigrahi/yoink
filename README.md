# Yoink

> Just yoink it from the swarm.

Yoink is a desktop torrent client for Windows. It searches public torrent
sites, downloads with libtorrent, and plays a video while it is still
downloading. The shell is PyQt6 and the UI is HTML/CSS/JS in a web view.

**Yoink is self-hosted.** There are no published downloads: you run it from
source, or build your own exe on your own machine.

- [Features](docs/FEATURES.md): what it does, and how the in-app player works
- [Development](docs/DEVELOPMENT.md): tests, lint, building an exe, code layout
- [TODO](TODO.md): known gaps and bugs

## How to run

You need Windows 10 or 11 (x64) and Python 3.10 or newer.

```powershell
git clone https://github.com/Hrishikesh-Panigrahi/yoink.git
cd yoink
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:PYTHONPATH = "$PWD;$PWD\src"
python src\main.py
```

Add `--minimized` to start in the tray with no window. With GNU Make installed,
`make install` then `make run` does the same thing.

Your library, settings and logs live in `%LOCALAPPDATA%\Yoink\`. To try things
without touching them, point `TORRENT_DB_PATH` at another file first:

```powershell
$env:TORRENT_DB_PATH = "$env:TEMP\yoink-dev.db"
```

The in-app player needs VLC. Install it, or, without admin rights, unzip VLC's
[portable build](https://www.videolan.org/vlc/download-windows.html) into
`%LOCALAPPDATA%\Yoink\vlc`. Without VLC everything else works and the Play
button stays hidden.

To get an exe instead, run `python build.py`. It writes `dist/Yoink.exe`, plus
an installer if Inno Setup is installed (see
[Development](docs/DEVELOPMENT.md#build-an-exe-and-installer)).

## Sources and DNS

Search goes to the sites enabled in Settings → Sources (1337x, TorrentGalaxy
and Nyaa out of the box) and falls back to The Pirate Bay's API if they return
nothing. "Stable APIs only" in the source filter skips straight to The Pirate
Bay.

YTS is **off** by default: `yts.mx` no longer publishes an A record, and leaving
it on cost every search two 10-second connect timeouts.

Some networks answer DNS for torrent sites with a sinkhole address, which makes
every source look permanently offline. Yoink therefore resolves source
hostnames over DNS-over-HTTPS (Cloudflare, then Google) instead of the local
resolver — on one such connection that took reachable sources from 2 to 11.
Turn it off in Settings → Library & app behavior to use your system resolver.

It works by replacing `socket.getaddrinfo` (see
[`src/utils/resolver.py`](src/utils/resolver.py)), not by rewriting URLs to raw
IPs, which would break SNI, the `Host` header and certificate validation.

DNS is not a cure-all. A site blocked at the TLS layer still resets the
connection, and one behind DDoS-Guard or Cloudflare returns a challenge page
instead of results. For those, use the proxy setting in Settings → Advanced, or
see the Torznab note in [TODO.md](TODO.md).

## Legal note

Yoink is a torrent client. It does not host, bundle, or endorse copyrighted
content. You are responsible for using torrents and magnet links legally in your
region.
