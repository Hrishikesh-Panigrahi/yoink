# Features

Everything below is implemented and reachable from the UI. Where sources come
from, and why YTS is off, is covered in the
[README](../README.md#sources-and-dns).

## Search

- **Two provider modes.** `multi` searches the sites you have enabled and is the
  default ("All my enabled sites"). `stable` queries The Pirate Bay's API
  directly and is the fastest. YTS can be switched on as a stable source, but
  is off by default.
- **Filters.** Region (Bollywood, Hollywood, South Indian, Korean, anime),
  category (movies, TV, anime, music, games, apps, books), quality, and sort by
  relevance, seeds, size or newest.
- **Health ranking.** Results are scored on seeders, quality and source weight,
  then deduplicated by infohash so one release doesn't appear five times.
- **Provider health checks.** Every source can be pinged with a small test
  search and graded into three bands, so you can see what's reachable and turn
  off what isn't. Sources can be enabled individually.
- **Safety flags.** Results are scanned for common red flags: an `.exe` inside
  something claiming to be a film, a file far too small for its stated quality,
  password-protected archives.
- **TMDB metadata.** With a free API key, results gain posters, backdrops,
  ratings, runtime, genres, plot and a trailer link. Responses are cached.
- **Search history**, recalled as you type.

## Transfers

- Add by magnet link, `.torrent` file, or drag and drop.
- Per-file priorities, so you can skip the extras inside a torrent.
- Pause and resume individually or across the whole queue.
- Move a torrent to a different folder after it has started.
- Remove with or without deleting the data.
- Labels for grouping a library.
- Fast-resume data is written per torrent, so progress survives a restart.
- Open the finished file or reveal it in Explorer.
- Play a video while it is still downloading (see
  [below](#playing-a-file-while-it-downloads)).

## Automation

- **Watch folder.** Drop a `.torrent` into a directory and it gets added.
- **RSS feeds.** Subscribe with an optional title regex and a minimum-seeder
  floor. Seen items are tracked so nothing is added twice.
- **Clipboard watcher.** Copy a magnet link, switch to Yoink, and it offers to
  add it.
- **Scheduled bandwidth.** Apply quieter caps during a chosen window.
- **File associations.** The installer can register `magnet:` links and
  `.torrent` files. A single-instance guard hands the path to the running
  window instead of opening a second one.

## Limits

Global download and upload caps, a limit on how many torrents download and seed
at once, and a seed ratio limit that pauses a torrent once it is reached.

## Application

- Eight themes. Minimise to tray and keep seeding.
- Native notifications when a download finishes.
- Optional launch at login.
- Command palette and keyboard shortcuts.
- Export and import settings.
- Proxy support (`http`, `https`, `socks5`) with a custom user agent.
- Settings live in a SQLite file under `%LOCALAPPDATA%\Yoink\`. No account, no
  telemetry.

## Playing a file while it downloads

A **Play** button appears on any search result with a magnet, and on any
download whose torrent contains a video. From a search result Yoink adds the
magnet, waits for the file list, switches to sequential pieces and buffers the
head before opening the player — the button reports which of those it is on.

The download-row button behaves the same way once the torrent is already added.
It switches libtorrent to sequential order, deadlines the head *and* the tail of
the file, and opens the file in an in-app window — you do not have to wait for
the download to finish.

The tail is prioritised alongside the head on purpose: MP4 keeps its `moov`
index at the end unless the file was written for streaming, and Matroska keeps
its cues there, so a player that cannot see the tail reports an unknown duration
and refuses to seek.

Playing a file that is still downloading needs more than sequential pieces.
VLC's ordinary file access reports end-of-stream at the last byte on disk, so
opening a torrent at 25% plays exactly 25% and stops — measured, not assumed.
Yoink therefore feeds VLC through `libvlc_media_new_callbacks`
(`src/player/source.py`), whose read callback blocks at the current end of the
file and waits for the missing bytes. The torrent's final size is handed to VLC
as the real stream length, so duration and seeking behave from the start.

### Where the VLC runtime comes from

Playback is libVLC via [`python-vlc`](https://pypi.org/project/python-vlc/).
That package is only a ctypes binding — it needs an actual VLC runtime, which an
exe from `build.py` carries inside it. Otherwise Yoink looks for one in this
order:

1. `YOINK_VLC_DIR`, if you point it at a folder holding `libvlc.dll` and
   `plugins/`.
2. The copy bundled inside a frozen build.
3. A portable copy under `%LOCALAPPDATA%\Yoink\vlc` — installing VLC properly
   needs administrator rights, and unzipping VLC's official
   [portable build](https://www.videolan.org/vlc/download-windows.html) here
   does not.
4. An installed VLC, via the registry then `C:\Program Files\VideoLAN\VLC`.

With none of those, everything else works and the Play button simply stays
hidden; `getPlayerStatus` reports why.

QtMultimedia was the alternative and was rejected: on Windows it goes through
Media Foundation, which is patchy on exactly the MKV, HEVC and AC3 combinations
torrents ship. The cost of libVLC is roughly 40-50 MB of plugins in the build.
