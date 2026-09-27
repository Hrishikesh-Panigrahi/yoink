from __future__ import annotations

import os
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, SavedTorrent, Setting
from utils.logger import setup_logger
from utils.paths import default_db_path

logger = setup_logger("db")

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def init_db(db_path: Optional[str] = None) -> Engine:
    """Create the engine and tables. Safe to call more than once.

    The path is `db_path`, else `TORRENT_DB_PATH`, else `yoink.db` in the app data folder.
    """
    global _engine, _SessionLocal

    if _engine is not None and db_path is None:
        return _engine

    resolved = db_path or os.environ.get("TORRENT_DB_PATH") or default_db_path()
    parent = os.path.dirname(resolved)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    logger.info(f"Initializing database at {resolved}")
    _engine = create_engine(f"sqlite:///{resolved}")
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine)

    _ensure_default_settings()
    return _engine


def dispose_engine() -> None:
    """Used by tests."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def _session() -> Session:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    return _SessionLocal()


def _ensure_default_settings() -> None:
    if get_setting("default_download_dir") is None:
        set_setting("default_download_dir", os.path.expanduser("~/Downloads"))


def get_setting(key: str) -> Optional[str]:
    try:
        with _session() as session:
            row = session.query(Setting).filter_by(key=key).first()
            return row.value if row else None
    except Exception as exc:
        logger.error(f"get_setting({key}) failed: {exc}")
        return None


def get_all_settings() -> dict:
    try:
        with _session() as session:
            rows = session.query(Setting).all()
            return {r.key: r.value for r in rows}
    except Exception as exc:
        logger.error(f"get_all_settings failed: {exc}")
        return {}


def set_setting(key: str, value: str) -> None:
    try:
        with _session() as session:
            row = session.query(Setting).filter_by(key=key).first()
            if row is None:
                session.add(Setting(key=key, value=value))
            elif row.value != value:
                row.value = value
            session.commit()
    except Exception as exc:
        logger.error(f"set_setting({key}={value}) failed: {exc}")


def save_torrent(
    info_hash: str, name: str, magnet_link: str, save_path: str, size: int = 0
) -> None:
    try:
        with _session() as session:
            row = session.query(SavedTorrent).filter_by(info_hash=info_hash).first()
            if row is None:
                session.add(
                    SavedTorrent(
                        info_hash=info_hash,
                        name=name,
                        magnet_link=magnet_link,
                        size=size,
                        save_path=save_path,
                    )
                )
            else:
                row.name = name or row.name
                row.magnet_link = magnet_link or row.magnet_link
                row.save_path = save_path or row.save_path
                if size:
                    row.size = size
            session.commit()
    except Exception as exc:
        logger.error(f"save_torrent({info_hash}) failed: {exc}")


def update_torrent_status(info_hash: str, status: str) -> None:
    try:
        with _session() as session:
            row = session.query(SavedTorrent).filter_by(info_hash=info_hash).first()
            if row is not None:
                row.status = status
                session.commit()
    except Exception as exc:
        logger.error(f"update_torrent_status({info_hash}) failed: {exc}")


def remove_torrent(info_hash: str) -> bool:
    try:
        with _session() as session:
            row = session.query(SavedTorrent).filter_by(info_hash=info_hash).first()
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
    except Exception as exc:
        logger.error(f"remove_torrent({info_hash}) failed: {exc}")
        return False


def list_torrents() -> List[SavedTorrent]:
    try:
        with _session() as session:
            return session.query(SavedTorrent).all()
    except Exception as exc:
        logger.error(f"list_torrents failed: {exc}")
        return []
