from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from .models import Base, Torrent, TorrentFile
import os
from utils.logger import setup_logger

# Set up logger
logger = setup_logger('database')

class DatabaseManager:
    def __init__(self, db_path: str = "torrent.db"):
        logger.info(f"Initializing DatabaseManager with database path: {db_path}")
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.debug("Database engine and session maker initialized")
        
    def get_session(self) -> Session:
        return self.Session()
        
    def add_torrent(self, name: str, magnet_link: str, info_hash: str, size: int, save_path: str) -> Torrent:
        logger.info(f"Adding new torrent: {name} (hash: {info_hash})")
        try:
            with self.get_session() as session:
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
        logger.debug(f"Updating torrent status: {info_hash} -> {status}")
        try:
            with self.get_session() as session:
                torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
                if torrent:
                    torrent.status = status
                    session.commit()
                    logger.debug(f"Status updated successfully for torrent: {torrent.name}")
                else:
                    logger.warning(f"Torrent not found with hash: {info_hash}")
        except Exception as e:
            logger.error(f"Failed to update torrent status: {str(e)}", exc_info=True)
            raise
                
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