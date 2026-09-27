# Features

Everything here works today and can be reached from the app. For where search
results come from, see the [README](../README.md#sources-and-dns).

## Search

- Two ways to search. "All my enabled sites" is the default and searches The
  Pirate Bay plus every site you've turned on. "Stable APIs only" asks only The
  Pirate Bay's API, which is the fastest.
- Filters for region (Bollywood, Hollywood, South Indian, Korean, anime),
  category (movies, TV, anime, music, games, apps, books) and quality. You can
  sort by relevance, seeders, size or date.
- The category filter works on every source. Sites that support it are asked
  for the category; for the rest, Yoink goes by the category the site gives
  each result, or by the title.
- Results are scored on seeders, quality and which site they came from.
  Duplicates are merged by infohash, so the same release doesn't show up five
  times.
- Each source can be checked with a small test search. It gets marked as
  working, slow or down, so you can see which ones are reachable and turn off
  the rest.
- Suspicious results get a warning, for example an `.exe` inside something that
  says it's a film, a file far too small for the quality it claims, or a
  password-protected archive.
- With a free TMDB API key, results also show posters, ratings, runtime,
  genres, a plot summary and a trailer link. These are cached.
- Your past searches come up as you type.

## Downloads

- Add torrents with a magnet link, a `.torrent` file, or by dragging either onto
  the window.
- Pick which files inside a torrent you want, so you can skip the extras.
- Pause and resume one torrent or all of them.
- Move a torrent to another folder after it has started.
- Remove a torrent and choose whether to keep the downloaded files.
- Group your library with labels.
- Progress is saved for each torrent, so nothing is lost when you restart.
- Open a finished file, or show it in Explorer.
- Watch a video while it's still downloading (see
  [below](#playing-a-file-while-it-downloads)).

## Automation

- Watch folder: drop a `.torrent` file into a folder you choose and Yoink adds
  it.
- RSS feeds: subscribe to a feed, optionally with a title pattern and a minimum
  number of seeders. Yoink remembers what it has already added.
- Clipboard: copy a magnet link, switch to Yoink, and it offers to add it.
- Scheduled bandwidth: use lower speed limits during hours you pick.
- File associations: the installer can make `magnet:` links and `.torrent`
  files open in Yoink. If Yoink is already running, the link goes to that window
  instead of starting a second copy.

## Limits

You can cap download and upload speed, limit how many torrents download and
seed at the same time, and set a seed ratio after which a torrent pauses.

## General

- Eight themes. Yoink can minimise to the tray and keep seeding there.
- A notification when a download finishes.
- Optional launch at login.
- A command palette and keyboard shortcuts.
- Export and import your settings.
- An HTTP or HTTPS proxy for searches, with an optional custom user agent (see the
  [README](../README.md#using-a-proxy)).
- Settings are kept in a SQLite file in `%LOCALAPPDATA%\Yoink\`. There's no
  account and no telemetry.

## Playing a file while it downloads

A Play button shows up on search results that have a magnet link, and on any
download that contains a video.

When you press Play on a search result, Yoink adds the magnet, waits for the
list of files, switches to downloading the pieces in order, and buffers the
start of the video before opening the player. The button tells you which of
those steps it's on.

The Play button on a download does the same once the torrent is already there.
It asks libtorrent to download pieces in order, gives priority to both the
start and the end of the file, and opens the video in a player window while the
rest keeps downloading.

The end of the file matters as much as the start. MP4 files usually keep their
index (`moov`) at the end, and MKV files keep their seek points there. Without
it, the player can't show the length of the video or let you skip ahead.

Downloading in order isn't enough on its own. VLC normally stops playing at the
last byte that's on disk, so a video that's 25% downloaded plays for 25% and
then stops. Yoink gets around this by feeding VLC through
`libvlc_media_new_callbacks` (see `src/player/source.py`). When VLC asks for
data that hasn't arrived yet, Yoink waits for it instead of reporting the end of
the file. It also tells VLC the full size of the file up front, so the length
and seeking work straight away.

### Where VLC comes from

Playback uses libVLC through [`python-vlc`](https://pypi.org/project/python-vlc/),
which is only a thin wrapper and needs VLC itself to be present. An exe built
with `build.py` includes VLC. Otherwise Yoink looks for it in this order:

1. The folder in `YOINK_VLC_DIR`, if you've set it. It needs `libvlc.dll` and a
   `plugins/` folder.
2. The copy included in a built exe.
3. A portable copy in `%LOCALAPPDATA%\Yoink\vlc`. Installing VLC normally
   needs admin rights, but unzipping the
   [portable version](https://www.videolan.org/vlc/download-windows.html) there
   doesn't.
4. An installed VLC, found through the registry or in
   `C:\Program Files\VideoLAN\VLC`.

If none of those are there, everything else still works and the Play button
stays hidden. The `getPlayerStatus` bridge call says why.

QtMultimedia was the other option. It wasn't used because on Windows it relies
on Media Foundation, which struggles with the MKV, HEVC and AC3 files that are
common on torrent sites. The downside of VLC is that it adds about 40 to 50 MB
to the build.
