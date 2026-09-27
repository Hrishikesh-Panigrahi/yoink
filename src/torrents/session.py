"""libtorrent session lifecycle and tuning.

`Session` is the only stateful object in the torrents layer. It holds the
libtorrent session, the alert-pump thread, the handle cache and the current save
path. Everything else in the package is a plain function that takes a `Session`
first.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict

import libtorrent as lt

from torrents.dto import NetworkStats
from torrents.resume import store_resume_data
from utils.logger import setup_logger
from utils.paths import normalize_path

logger = setup_logger("torrents.session")

#: Applied at startup so libtorrent's conservative defaults do not throttle downloads.
_OPTIMIZED_SETTINGS = {
    "active_downloads": -1,
    "active_seeds": -1,
    "active_limit": -1,
    "connections_limit": 500,
    "tick_interval": 100,
    "cache_size": 16 * 1024,
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
    lt_session: lt.session
    save_path: str
    handles: Dict[str, lt.torrent_handle] = field(default_factory=dict)
    #: info hash -> index of the file currently being streamed, if any.
    streams: Dict[str, int] = field(default_factory=dict)
    _stop: threading.Event = field(default_factory=threading.Event)
    _pump: threading.Thread | None = None


def create_session(save_path: str) -> Session:
    """Start a libtorrent session and its alert-pump thread."""
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
    logger.info("Stopping libtorrent session")
    for handle in list(session.handles.values()):
        if handle is not None and handle.is_valid():
            try:
                handle.save_resume_data()
            except Exception as exc:
                logger.debug(f"save_resume_data request failed during shutdown: {exc}")
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
    """Rates are in KB/s. 0 or negative means unlimited, None leaves a value as is."""
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
    """Returns how many torrents were paused. `max_ratio <= 0` turns this off."""
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
    """Set the default save path for new torrents. Returns it normalized."""
    session.save_path = normalize_path(path)
    logger.info(f"Save path set to {session.save_path}")
    return session.save_path


def network_stats(session: Session) -> NetworkStats:
    status = session.lt_session.status()
    return NetworkStats(
        download_kb_s=status.download_rate / 1024.0,
        upload_kb_s=status.upload_rate / 1024.0,
    )


def _pump_alerts(session: Session) -> None:
    while not session._stop.is_set():
        try:
            session.lt_session.post_torrent_updates()
            _handle_alerts(session)
        except Exception as exc:
            logger.error(f"Alert pump error: {exc}")
            session._stop.wait(1.0)
            continue
        session._stop.wait(0.1)


def _handle_alerts(session: Session) -> None:
    try:
        alerts = session.lt_session.pop_alerts()
    except Exception as exc:
        logger.debug(f"pop_alerts failed: {exc}")
        return

    for alert in alerts:
        alert_name = type(alert).__name__
        if alert_name == "save_resume_data_alert":
            handle = alert.handle
            if handle.is_valid():
                info_hash = str(handle.info_hash()).lower()
                store_resume_data(info_hash, alert.params)
        elif alert_name == "metadata_received_alert":
            handle = alert.handle
            if handle.is_valid():
                try:
                    handle.save_resume_data()
                except Exception as exc:
                    logger.debug(f"save_resume_data request failed after metadata: {exc}")
        elif alert_name == "torrent_error_alert":
            try:
                info_hash = str(alert.handle.info_hash()).lower()
            except Exception:
                info_hash = "unknown"
            logger.warning(f"Torrent error for {info_hash}: {alert.message()}")
