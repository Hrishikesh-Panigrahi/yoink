from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Torrent(Base):
    """Torrent table for storing torrent information"""
    __tablename__ = 'torrents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    magnet_link = Column(Text)
    info_hash = Column(String(40), unique=True)
    size = Column(Integer, default=0)
    status = Column(String(20), default='downloading')
    save_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    files = relationship("TorrentFile", back_populates="torrent", cascade="all, delete-orphan")
    
class TorrentFile(Base):
    """Torrent files table for storing individual file information"""
    __tablename__ = 'torrent_files'
    
    id = Column(Integer, primary_key=True)
    torrent_id = Column(Integer, ForeignKey('torrents.id'))
    name = Column(String(255))
    size = Column(Integer)
    progress = Column(Float, default=0.0)
    is_selected = Column(Boolean, default=True)
    
    torrent = relationship("Torrent", back_populates="files") 