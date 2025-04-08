import sqlite3
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from utils.logger import setup_logger

# Set up logger
logger = setup_logger('database_manager')

@dataclass
class SavedTorrent:
    """Data class for saved torrent information"""
    name: str
    magnet_link: str
    save_path: str
    hash: Optional[str] = None

class DatabaseManager:
    def __init__(self, db_path: str = "torrent.db"):
        """Initialize the database manager"""
        self.db_path = db_path
        self._init_db()
        logger.info(f"Initialized DatabaseManager with database path: {db_path}")

    def _init_db(self):
        """Initialize the database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create torrents table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS torrents (
                        hash TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        magnet_link TEXT NOT NULL,
                        save_path TEXT NOT NULL,
                        size TEXT DEFAULT 'Calculating...',
                        status TEXT DEFAULT 'Queued',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("Database schema initialized")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def add_torrent(self, hash: str, name: str, magnet_link: str, save_path: str) -> bool:
        """Add a torrent to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO torrents (hash, name, magnet_link, save_path) VALUES (?, ?, ?, ?)",
                    (hash, name, magnet_link, save_path)
                )
                conn.commit()
                logger.info(f"Added torrent to database: {name}")
                return True
        except Exception as e:
            logger.error(f"Error adding torrent to database: {e}")
            return False

    def remove_torrent(self, hash: str) -> bool:
        """Remove a torrent from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM torrents WHERE hash = ?", (hash,))
                conn.commit()
                logger.info(f"Removed torrent from database: {hash}")
                return True
        except Exception as e:
            logger.error(f"Error removing torrent from database: {e}")
            return False

    def get_all_torrents(self) -> List[SavedTorrent]:
        """Get all saved torrents"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT hash, name, magnet_link, save_path FROM torrents")
                rows = cursor.fetchall()
                
                torrents = []
                for row in rows:
                    torrents.append(SavedTorrent(
                        hash=row[0],
                        name=row[1],
                        magnet_link=row[2],
                        save_path=row[3]
                    ))
                
                logger.info(f"Retrieved {len(torrents)} torrents from database")
                return torrents
                
        except Exception as e:
            logger.error(f"Error getting torrents from database: {e}")
            return []

    def get_torrent(self, hash: str) -> Optional[SavedTorrent]:
        """Get a specific torrent by hash"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT hash, name, magnet_link, save_path FROM torrents WHERE hash = ?",
                    (hash,)
                )
                row = cursor.fetchone()
                
                if row:
                    return SavedTorrent(
                        hash=row[0],
                        name=row[1],
                        magnet_link=row[2],
                        save_path=row[3]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting torrent from database: {e}")
            return None 