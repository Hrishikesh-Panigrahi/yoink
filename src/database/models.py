from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Torrent(Base):
    __tablename__ = 'torrents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    magnet_link = Column(String)
    info_hash = Column(String, unique=True)
    size = Column(Integer)
    status = Column(String)
    save_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    files = relationship("TorrentFile", back_populates="torrent", cascade="all, delete-orphan")
    
class TorrentFile(Base):
    __tablename__ = 'torrent_files'
    
    id = Column(Integer, primary_key=True)
    torrent_id = Column(Integer, ForeignKey('torrents.id'))
    name = Column(String)
    size = Column(Integer)
    progress = Column(Float, default=0.0)
    is_selected = Column(Boolean, default=True)
    
    torrent = relationship("Torrent", back_populates="files") 