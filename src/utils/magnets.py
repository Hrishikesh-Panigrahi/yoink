"""Magnet URI builders shared between providers and torrent actions."""

from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import quote

DEFAULT_TRACKERS: tuple[str, ...] = (
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:80",
    "udp://tracker.coppersurfer.tk:6969/announce",
    "udp://tracker.leechers-paradise.org:6969/announce",
    "udp://tracker.internetwarriors.net:1337/announce",
    "udp://tracker.cyberia.is:6969/announce",
)


def build_magnet(info_hash: str, name: str, trackers: Optional[Iterable[str]] = None) -> str:
    """Build a `magnet:?xt=urn:btih:<hash>` URL with name and trackers."""
    tracker_list = list(trackers) if trackers is not None else list(DEFAULT_TRACKERS)
    tracker_params = "&".join(f"tr={quote(tracker)}" for tracker in tracker_list)
    base = f"magnet:?xt=urn:btih:{info_hash}&dn={quote(name)}"
    return f"{base}&{tracker_params}" if tracker_params else base
