from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Torrent(Base):
    """SQLAlchemy model for torrents"""
    __tablename__ = 'torrents'
    
    id = Column(Integer, primary_key=True)
    info_hash = Column(String(40), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    magnet_link = Column(Text, nullable=False)
    size = Column(BigInteger, default=0)
    status = Column(String(50), default='Downloading')
    save_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    files = relationship("TorrentFile", back_populates="torrent", cascade="all, delete-orphan")

class TorrentFile(Base):
    """SQLAlchemy model for torrent files"""
    __tablename__ = 'torrent_files'
    
    id = Column(Integer, primary_key=True)
    torrent_id = Column(Integer, ForeignKey('torrents.id'), nullable=False)
    name = Column(String(255), nullable=False)
    size = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    priority = Column(Integer, default=0)
    
    # Relationships
    torrent = relationship("Torrent", back_populates="files") 