"""SQLAlchemy models for the local SQLite database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True)
    value = Column(Text)


class SavedTorrent(Base):
    __tablename__ = "torrents"

    id = Column(Integer, primary_key=True)
    info_hash = Column(String(40), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    magnet_link = Column(Text, nullable=False)
    size = Column(BigInteger, default=0)
    status = Column(String(50), default="downloading")
    save_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
