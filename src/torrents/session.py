"""libtorrent session lifecycle and tuning.

`Session` is the one stateful holder in the torrents layer — it groups
the libtorrent session, the alert-pump thread, our handle cache, and
the current save path. All public operations are module-level functions
in this package that take a `Session` as the first argument.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict

import libtorrent as lt

from torrents.dto import NetworkStats
from utils.logger import setup_logger
from utils.paths import normalize_path

logger = setup_logger("torrents.session")

#: Settings applied on session start so downloads aren't throttled by libtorrent defaults.
_OPTIMIZED_SETTINGS = {
    "active_downloads": -1,
    "active_seeds": -1,
    "active_limit": -1,
    "connections_limit": 500,
    "tick_interval": 100,
    "cache_size": 1024 * 1024 * 1024,
    "disk_io_read_mode": 2,
    "disk_io_write_mode": 2,
    "enable_dht": True,
    "enable_lsd": True,
    "enable_upnp": True,
    "enable_natpmp": True,
    "upload_rate_limit": 0,
    "download_rate_limit": 0,
    "dht_max_peers": 500,
    "dht_max_fail_count": 20,
    "dht_max_torrents": 2000,
    "dht_max_dht_items": 2000,
    "dht_search_branching": 10,
    "dht_max_peers_reply": 100,
    "dht_restrict_routing_ips": True,
    "dht_max_torrent_search_reply": 20,
    "connection_speed": 200,
    "peer_connect_timeout": 2,
    "request_timeout": 10,
    "peer_timeout": 20,
    "enable_incoming_utp": True,
    "enable_outgoing_utp": True,
    "enable_incoming_tcp": True,
    "enable_outgoing_tcp": True,
    "max_peerlist_size": 4000,
    "max_failcount": 20,
    "close_redundant_connections": True,
    "alert_mask": lt.alert.category_t.all_categories,
}


@dataclass
class Session:
    """Mutable wrapper that holds everything the torrents layer needs."""

    lt_session: lt.session
    save_path: str
    handles: Dict[str, lt.torrent_handle] = field(default_factory=dict)
    _stop: threading.Event = field(default_factory=threading.Event)
    _pump: threading.Thread | None = None


def create_session(save_path: str) -> Session:
    """Create, optimize, and start a new libtorrent session pumping alerts."""
    lt_session = lt.session()
    lt_session.apply_settings(_OPTIMIZED_SETTINGS)
    lt_session.start_dht()
    lt_session.start_lsd()
    lt_session.start_upnp()
    lt_session.start_natpmp()

    session = Session(lt_session=lt_session, save_path=normalize_path(save_path))
    session._pump = threading.Thread(
        target=_pump_alerts, args=(session,), name="lt-alerts", daemon=True
    )
    session._pump.start()
    logger.info(f"libtorrent session ready (save_path={session.save_path})")
    return session


def stop_session(session: Session) -> None:
    """Stop the alert pump and shut libtorrent's background services down."""
    logger.info("Stopping libtorrent session")
    session._stop.set()
    if session._pump is not None:
        session._pump.join(timeout=2.0)
    try:
        session.lt_session.stop_dht()
        session.lt_session.stop_lsd()
        session.lt_session.stop_upnp()
        session.lt_session.stop_natpmp()
    except Exception as exc:
        logger.error(f"Session shutdown error: {exc}")


def apply_limits(
    session: Session,
    *,
    download_kb_s: int | None = None,
    upload_kb_s: int | None = None,
    active_downloads: int | None = None,
    active_seeds: int | None = None,
) -> None:
    """Apply runtime bandwidth / concurrency limits to the live session.

    Pass ``0`` (or negative) for unlimited. ``None`` leaves the value untouched.
    """
    patch: dict = {}
    if download_kb_s is not None:
        patch["download_rate_limit"] = max(0, int(download_kb_s)) * 1024
    if upload_kb_s is not None:
        patch["upload_rate_limit"] = max(0, int(upload_kb_s)) * 1024
    if active_downloads is not None:
        patch["active_downloads"] = -1 if active_downloads <= 0 else int(active_downloads)
    if active_seeds is not None:
        patch["active_seeds"] = -1 if active_seeds <= 0 else int(active_seeds)
        if active_seeds > 0 and active_downloads is not None and active_downloads > 0:
            patch["active_limit"] = int(active_downloads) + int(active_seeds)
    if patch:
        session.lt_session.apply_settings(patch)
        logger.info(f"Applied session limits: {patch}")


def enforce_seed_ratio(session: Session, max_ratio: float) -> int:
    """Pause any torrent that has hit the configured share ratio.

    Returns the number of torrents paused. ``max_ratio <= 0`` disables enforcement.
    """
    if max_ratio is None or max_ratio <= 0:
        return 0
    paused = 0
    for info_hash, handle in list(session.handles.items()):
        if handle is None or not handle.is_valid():
            continue
        status = handle.status()
        if status.total_done <= 0 or status.paused:
            continue
        ratio = status.all_time_upload / max(status.all_time_download, status.total_done)
        if ratio >= max_ratio:
            handle.pause()
            paused += 1
            logger.info(f"Seed ratio {ratio:.2f} reached for {info_hash}; paused")
    return paused


def set_save_path(session: Session, path: str) -> str:
    """Normalize and remember the default save path for new torrents."""
    session.save_path = normalize_path(path)
    logger.info(f"Save path set to {session.save_path}")
    return session.save_path


def network_stats(session: Session) -> NetworkStats:
    """Current session throughput in KB/s."""
    status = session.lt_session.status()
    return NetworkStats(
        download_kb_s=status.download_rate / 1024.0,
        upload_kb_s=status.upload_rate / 1024.0,
    )


def _pump_alerts(session: Session) -> None:
    """Background loop that drives libtorrent's update/alert pipeline."""
    while not session._stop.is_set():
        try:
            session.lt_session.post_torrent_updates()
        except Exception as exc:
            logger.error(f"Alert pump error: {exc}")
            session._stop.wait(1.0)
            continue
        session._stop.wait(0.1)
