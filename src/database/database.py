from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from .models import Base, Torrent, TorrentFile
import os

class DatabaseManager:
    def __init__(self, db_path: str = "torrent.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def get_session(self) -> Session:
        return self.Session()
        
    def add_torrent(self, name: str, magnet_link: str, info_hash: str, size: int, save_path: str) -> Torrent:
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
            return torrent
            
    def update_torrent_status(self, info_hash: str, status: str):
        with self.get_session() as session:
            torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
            if torrent:
                torrent.status = status
                session.commit()
                
    def add_torrent_files(self, info_hash: str, files: list):
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
                
    def update_file_progress(self, info_hash: str, file_name: str, progress: float):
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
                    
    def get_torrent(self, info_hash: str) -> Torrent:
        with self.get_session() as session:
            return session.query(Torrent).filter_by(info_hash=info_hash).first()
            
    def get_all_torrents(self) -> list:
        with self.get_session() as session:
            return session.query(Torrent).all()
            
    def delete_torrent(self, info_hash: str):
        with self.get_session() as session:
            torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
            if torrent:
                session.delete(torrent)
                session.commit() 