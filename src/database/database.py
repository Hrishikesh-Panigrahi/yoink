from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from datetime import datetime
import os
from pathlib import Path
from typing import Optional, List, Dict
from src.utils.logger import setup_logger
from .models import Base, Torrent, TorrentFile

# Set up logger
logger = setup_logger('database')

class Setting(Base):
    """Settings table"""
    __tablename__ = 'settings'
    
    key = Column(String(50), primary_key=True)
    value = Column(Text)

class DownloadHistory(Base):
    """Download history table"""
    __tablename__ = 'download_history'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    magnet = Column(Text)
    size = Column(String(50))
    status = Column(String(20))
    progress = Column(Float, default=0.0)
    download_speed = Column(String(50))
    added_date = Column(DateTime, default=datetime.utcnow)
    completed_date = Column(DateTime, nullable=True)
    save_path = Column(String(255))
    error = Column(Text, nullable=True)

class DatabaseManager:
    def __init__(self, db_path: str = "torrent.db"):
        """Initialize database connection"""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logger.info(f"Created database directory: {db_dir}")
            
            # Create database engine
            self.engine = create_engine(f'sqlite:///{db_path}')
            logger.info(f"Initializing DatabaseManager with database path: {db_path}")
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            logger.info("Database schema initialized")
            
            # Initialize default settings if needed
            self._init_default_settings()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _init_default_settings(self):
        """Initialize default settings if they don't exist"""
        try:
            # Set default download directory
            default_dir = os.path.expanduser("~/Downloads")
            if not self.get_setting('default_download_dir'):
                self.set_setting('default_download_dir', default_dir)
                logger.info(f"Setting updated: default_download_dir={default_dir}")
        except Exception as e:
            logger.error(f"Error initializing default settings: {e}")
            raise
        
    def get_session(self) -> Session:
        return sessionmaker(bind=self.engine)()
        
    def add_torrent(self, name: str, magnet_link: str, info_hash: str, size: int, save_path: str) -> Torrent:
        """Add a new torrent to the database"""
        logger.info(f"Adding new torrent: {name} (hash: {info_hash})")
        try:
            with self.get_session() as session:
                # Check if torrent already exists
                existing = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if existing:
                    logger.info(f"Torrent already exists: {name}")
                    return existing
                
                # Create new torrent
                torrent = Torrent(
                    name=name,
                    magnet_link=magnet_link,
                    info_hash=info_hash,
                    size=size,
                    status="downloading",
                    save_path=save_path
                )
                session.add(torrent)
                session.commit()
                logger.debug(f"Torrent added successfully: {name}")
                return torrent
        except Exception as e:
            logger.error(f"Failed to add torrent {name}: {str(e)}", exc_info=True)
            raise
            
    def update_torrent_status(self, info_hash: str, status: str):
        """Update the status of a torrent in the database"""
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if torrent:
                    torrent.status = status
                    session.commit()
                    logger.info(f"Updated torrent status: {info_hash} -> {status}")
                    return True
                else:
                    logger.warning(f"Torrent not found: {info_hash}")
                    return False
        except Exception as e:
            logger.error(f"Error updating torrent status: {e}")
            return False
                
    def add_torrent_files(self, info_hash: str, files: list):
        logger.info(f"Adding files for torrent: {info_hash}")
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if torrent:
                    for file_info in files:
                        file = TorrentFile(
                            torrent_id=torrent.id,
                            name=file_info['name'],
                            size=file_info['size'],
                            progress=0.0
                        )
                        session.add(file)
                    session.commit()
                    logger.debug(f"Added {len(files)} files for torrent: {torrent.name}")
                else:
                    logger.warning(f"Torrent not found with hash: {info_hash}")
        except Exception as e:
            logger.error(f"Failed to add torrent files: {str(e)}", exc_info=True)
            raise
                
    def update_file_progress(self, info_hash: str, file_name: str, progress: float):
        logger.debug(f"Updating file progress: {file_name} -> {progress}%")
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if torrent:
                    file = session.query(TorrentFile).filter_by(
                        torrent_id=torrent.id,
                        name=file_name
                    ).first()
                    if file:
                        file.progress = progress
                        session.commit()
                        logger.debug(f"File progress updated successfully: {file_name}")
                    else:
                        logger.warning(f"File not found: {file_name}")
                else:
                    logger.warning(f"Torrent not found with hash: {info_hash}")
        except Exception as e:
            logger.error(f"Failed to update file progress: {str(e)}", exc_info=True)
            raise
                    
    def get_torrent(self, info_hash: str) -> Torrent:
        logger.debug(f"Getting torrent with hash: {info_hash}")
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if not torrent:
                    logger.warning(f"Torrent not found with hash: {info_hash}")
                return torrent
        except Exception as e:
            logger.error(f"Failed to get torrent: {str(e)}", exc_info=True)
            raise
            
    def get_all_torrents(self) -> list:
        logger.debug("Getting all torrents")
        try:
            with self.get_session() as session:
                torrents = session.query(Torrent).all()
                logger.debug(f"Found {len(torrents)} torrents")
                return torrents
        except Exception as e:
            logger.error(f"Failed to get all torrents: {str(e)}", exc_info=True)
            raise
            
    def delete_torrent(self, info_hash: str):
        logger.info(f"Deleting torrent with hash: {info_hash}")
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if torrent:
                    session.delete(torrent)
                    session.commit()
                    logger.debug(f"Torrent deleted successfully: {torrent.name}")
                else:
                    logger.warning(f"Torrent not found with hash: {info_hash}")
        except Exception as e:
            logger.error(f"Failed to delete torrent: {str(e)}", exc_info=True)
            raise

    def get_setting(self, key: str) -> str:
        """Get setting value by key"""
        try:
            setting = self.get_session().query(Setting).filter_by(key=key).first()
            return setting.value if setting else None
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return None

    def set_setting(self, key: str, value: str):
        """Set setting value"""
        try:
            setting = self.get_session().query(Setting).filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
                self.get_session().add(setting)
            self.get_session().commit()
            logger.info(f"Setting updated: {key}={value}")
        except Exception as e:
            logger.error(f"Error setting {key}={value}: {e}")
            self.get_session().rollback()
            raise

    def add_download(self, name: str, magnet: str, size: str, save_path: str) -> int:
        """Add new download to history"""
        try:
            download = DownloadHistory(
                name=name,
                magnet=magnet,
                size=size,
                status="Queued",
                save_path=save_path
            )
            self.get_session().add(download)
            self.get_session().commit()
            logger.info(f"Added download to history: {name}")
            return download.id
        except Exception as e:
            logger.error(f"Error adding download to history: {e}")
            self.get_session().rollback()
            raise

    def update_download(self, download_id: int, **kwargs):
        """Update download history entry"""
        try:
            download = self.get_session().query(DownloadHistory).filter_by(id=download_id).first()
            if download:
                for key, value in kwargs.items():
                    setattr(download, key, value)
                    if key == 'status' and value == 'Completed':
                        download.completed_date = datetime.utcnow()
                self.get_session().commit()
                logger.info(f"Updated download history: {download.name}")
            else:
                logger.warning(f"Download not found: {download_id}")
        except Exception as e:
            logger.error(f"Error updating download history: {e}")
            self.get_session().rollback()
            raise

    def get_download_history(self, limit: int = None, status: str = None) -> list:
        """Get download history with optional filters"""
        try:
            query = self.get_session().query(DownloadHistory)
            if status:
                query = query.filter_by(status=status)
            query = query.order_by(DownloadHistory.added_date.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting download history: {e}")
            return []

    def get_active_downloads(self) -> list:
        """Get list of active downloads"""
        try:
            return self.get_session().query(DownloadHistory).filter(
                DownloadHistory.status.in_(['Queued', 'Downloading', 'Paused'])
            ).order_by(DownloadHistory.added_date.desc()).all()
        except Exception as e:
            logger.error(f"Error getting active downloads: {e}")
            return []

    def delete_download(self, download_id: int):
        """Delete download history entry"""
        try:
            download = self.get_session().query(DownloadHistory).filter_by(id=download_id).first()
            if download:
                self.get_session().delete(download)
                self.get_session().commit()
                logger.info(f"Deleted download history: {download.name}")
            else:
                logger.warning(f"Download not found: {download_id}")
        except Exception as e:
            logger.error(f"Error deleting download history: {e}")
            self.get_session().rollback()
            raise

    def clear_download_history(self):
        """Clear all download history"""
        try:
            self.get_session().query(DownloadHistory).delete()
            self.get_session().commit()
            logger.info("Download history cleared")
        except Exception as e:
            logger.error(f"Error clearing download history: {e}")
            self.get_session().rollback()
            raise

    def get_default_download_dir(self) -> str:
        """Get the default download directory from settings"""
        try:
            default_dir = self.get_setting('default_download_dir')
            if not default_dir:
                # If no default directory is set, use the user's downloads folder
                default_dir = os.path.expanduser("~/Downloads")
                self.set_setting('default_download_dir', default_dir)
            return default_dir
        except Exception as e:
            logger.error(f"Error getting default download directory: {e}")
            return os.path.expanduser("~/Downloads")

    def set_default_download_dir(self, directory: str):
        """Set the default download directory in settings"""
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
            self.set_setting('default_download_dir', directory)
            logger.info(f"Default download directory set to: {directory}")
        except Exception as e:
            logger.error(f"Error setting default download directory: {e}")
            raise

    def remove_torrent(self, info_hash: str) -> bool:
        """Remove a torrent from the database"""
        logger.info(f"Removing torrent with hash: {info_hash}")
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if torrent:
                    session.delete(torrent)
                    session.commit()
                    logger.info(f"Removed torrent: {torrent.name}")
                    return True
                else:
                    logger.warning(f"Torrent not found with hash: {info_hash}")
                    return False
        except Exception as e:
            logger.error(f"Error removing torrent: {e}")
            return False 