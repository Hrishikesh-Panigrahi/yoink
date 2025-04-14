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
    info_hash: Optional[str] = None

class DatabaseManager:
    def __init__(self, db_path: str = "torrent.db"):
        """Initialize the database manager"""
        self.db_path = db_path
        self.initialize_database()
        logger.info(f"Initialized DatabaseManager with database path: {db_path}")

    def initialize_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS saved_torrents (
                        info_hash TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        magnet_link TEXT NOT NULL,
                        save_path TEXT NOT NULL
                    )
                """)
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def _init_db(self):
        """Initialize the database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create torrents table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS torrents (
                        info_hash TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        magnet_link TEXT NOT NULL,
                        save_path TEXT NOT NULL,
                        size TEXT DEFAULT 'Calculating...',
                        status TEXT DEFAULT 'Queued',
                        source_type TEXT DEFAULT 'magnet',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Add source_type column if it doesn't exist
                try:
                    cursor.execute("ALTER TABLE torrents ADD COLUMN source_type TEXT DEFAULT 'magnet'")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
                
                conn.commit()
                logger.info("Database schema initialized")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def add_torrent(self, info_hash: str, name: str, magnet_link: str, save_path: str, source_type: str = 'magnet') -> bool:
        """Add a torrent to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO torrents (info_hash, name, magnet_link, save_path, source_type) VALUES (?, ?, ?, ?, ?)",
                    (info_hash, name, magnet_link, save_path, source_type)
                )
                conn.commit()
                logger.info(f"Added torrent to database: {name}")
                return True
        except Exception as e:
            logger.error(f"Error adding torrent to database: {e}")
            return False

    def remove_torrent(self, info_hash: str) -> bool:
        """Remove torrent from database by info_hash"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM saved_torrents
                    WHERE info_hash = ?
                """, (info_hash,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing torrent from database: {e}")
            return False

    def get_all_torrents(self) -> List[SavedTorrent]:
        """Get all saved torrents"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT info_hash, name, magnet_link, save_path FROM torrents")
                rows = cursor.fetchall()
                
                torrents = []
                for row in rows:
                    torrents.append(SavedTorrent(
                        info_hash=row[0],
                        name=row[1],
                        magnet_link=row[2],
                        save_path=row[3]
                    ))
                
                logger.info(f"Retrieved {len(torrents)} torrents from database")
                return torrents
                
        except Exception as e:
            logger.error(f"Error getting torrents from database: {e}")
            return []

    def get_torrent(self, info_hash: str) -> Optional[SavedTorrent]:
        """Get torrent from database by info_hash"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, magnet_link, save_path, info_hash
                    FROM saved_torrents
                    WHERE info_hash = ?
                """, (info_hash,))
                row = cursor.fetchone()
                if row:
                    return SavedTorrent(
                        name=row[0],
                        magnet_link=row[1],
                        save_path=row[2],
                        info_hash=row[3]
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting torrent from database: {e}")
            return None

    def _load_saved_torrents(self) -> List[SavedTorrent]:
        """Load saved torrents from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, magnet_link, save_path, info_hash
                    FROM saved_torrents
                """)
                rows = cursor.fetchall()
                return [
                    SavedTorrent(
                        name=row[0],
                        magnet_link=row[1],
                        save_path=row[2],
                        info_hash=row[3]
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error loading saved torrents: {e}")
            return []

    def save_torrent(self, torrent: SavedTorrent) -> bool:
        """Save torrent to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO saved_torrents (name, magnet_link, save_path, info_hash)
                    VALUES (?, ?, ?, ?)
                """, (torrent.name, torrent.magnet_link, torrent.save_path, torrent.info_hash))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving torrent: {e}")
            return False 