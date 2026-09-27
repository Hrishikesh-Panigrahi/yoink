"""In-app video playback through libvlc.

Nothing here imports `vlc` at module scope (see `player.runtime` for why). Import
`PlayerWindow` only after `is_available()` returns True, because it pulls in the
backend, which needs the library.
"""

from player.runtime import describe, is_available, load_vlc

__all__ = [
    "describe",
    "is_available",
    "load_vlc",
]
