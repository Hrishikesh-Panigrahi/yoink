"""In-app video playback, backed by libvlc.

Nothing here imports `vlc` at module scope — see `player.runtime` for why. Import
`PlayerWindow` only once `runtime.is_available()` says there is something to
render with; it pulls in the backend, which needs the library.
"""

from player.runtime import describe, is_available, load_vlc

__all__ = [
    "describe",
    "is_available",
    "load_vlc",
]
