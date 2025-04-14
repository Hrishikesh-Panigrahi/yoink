"""Implementation of torrent operations."""

import os
import logging
import libtorrent as lt
from typing import Dict, Optional, Union, List
from pathlib import Path
from PyQt6.QtCore import QTimer

from src.core.interfaces.torrent_operations import ITorrentOperations
from src.core.interfaces.torrent_session import ITorrentSession
from src.database.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger('torrent_operations')

class TorrentOperations(ITorrentOperations):
    """Implementation of torrent operations."""
    
    def __init__(self, session_manager: ITorrentSession, db_manager: DatabaseManager):
        """Initialize torrent operations.
        
        Args:
            session_manager: Manager for the libtorrent session
            db_manager: Manager for database operations
        """
        self.session_manager = session_manager
        self.db_manager = db_manager
        self.session = session_manager.session
        self.torrents = {}  # info_hash -> handle
        self.save_path = self.db_manager.get_default_download_dir()
        
        logger.info(f"TorrentOperations initialized with save path: {self.save_path}")
    
    def add_torrent(self, magnet_link: str, save_path: Optional[str] = None) -> str:
        """Add a torrent via magnet link.
        
        Args:
            magnet_link: The magnet link of the torrent to add
            save_path: The directory to save the downloaded files
            
        Returns:
            The info hash of the added torrent
            
        Raises:
            ValueError: If the magnet link is invalid
        """
        try:
            logger.info(f"Adding torrent from magnet link: {magnet_link[:60]}...")
            
            # Validate magnet link
            if not magnet_link.startswith('magnet:'):
                raise ValueError("Invalid magnet link format")
            
            # Set up save path
            if not save_path:
                save_path = self.save_path
            
            # Create save directory if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)
                logger.info(f"Created save directory: {save_path}")
            
            # Add torrent to session
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = save_path
            handle = self.session.add_torrent(params)
            
            # Get info hash
            info_hash = str(handle.info_hash()).lower()
            
            # Store handle
            self.torrents[info_hash] = handle
            
            # Add to database if we have metadata
            if handle.has_metadata():
                self._add_to_database(handle, magnet_link, save_path)
            else:
                # Enable metadata receiving alerts
                self.session.apply_settings({'alert_mask': lt.alert.category_t.status_notification})
                
                # Set up metadata received alert handler
                def check_metadata():
                    alerts = self.session.pop_alerts()
                    for alert in alerts:
                        if isinstance(alert, lt.metadata_received_alert):
                            if alert.handle.info_hash() == handle.info_hash():
                                self._add_to_database(alert.handle, magnet_link, save_path)
                                return True
                    return False
                
                # Start a timer to check for metadata
                timer = QTimer()
                timer.timeout.connect(lambda: check_metadata() and timer.stop())
                timer.start(1000)  # Check every second
                
                logger.debug(f"Waiting for metadata for torrent: {info_hash}")
            
            logger.info(f"Torrent added successfully with hash: {info_hash}")
            return info_hash
            
        except Exception as e:
            logger.error(f"Error adding torrent: {e}", exc_info=True)
            raise
    
    def add_torrent_file(self, torrent_file_path: Union[str, Path], save_path: Optional[str] = None) -> str:
        """Add a torrent via torrent file.
        
        Args:
            torrent_file_path: Path to the .torrent file
            save_path: The directory to save the downloaded files
            
        Returns:
            The info hash of the added torrent
            
        Raises:
            ValueError: If the torrent file is invalid
            FileNotFoundError: If the torrent file does not exist
        """
        try:
            # Convert to Path object if string
            file_path = Path(torrent_file_path)
            
            logger.info(f"Adding torrent from file: {file_path}")
            
            # Check if file exists
            if not file_path.exists():
                raise FileNotFoundError(f"Torrent file not found: {file_path}")
            
            # Set up save path
            target_save_path = save_path or self.save_path
            if not os.path.exists(target_save_path):
                os.makedirs(target_save_path)
                logger.info(f"Created save directory: {target_save_path}")
            
            # Read torrent file
            with open(file_path, 'rb') as f:
                torrent_data = f.read()
            
            # Create info object from torrent data
            info = lt.torrent_info(lt.bdecode(torrent_data))
            
            # Create torrent params
            params = lt.add_torrent_params()
            params.ti = info
            params.save_path = target_save_path
            
            # Add torrent to session
            handle = self.session.add_torrent(params)
            
            # Extract info hash
            info_hash = str(handle.info_hash()).lower()
            
            # Store handle in dictionary
            self.torrents[info_hash] = handle
            
            # Add to database
            self._add_to_database(handle, str(file_path), target_save_path)
            
            logger.info(f"Torrent added successfully with hash: {info_hash}")
            return info_hash
            
        except FileNotFoundError as e:
            logger.error(f"Torrent file not found: {torrent_file_path}")
            raise
        except Exception as e:
            logger.error(f"Error adding torrent file: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to add torrent file: {str(e)}") from e
    
    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent.
        
        Args:
            info_hash: The info hash of the torrent to remove
            delete_files: Whether to delete the downloaded files
            
        Returns:
            True if the torrent was removed successfully, False otherwise
        """
        try:
            logger.info(f"Removing torrent with hash: {info_hash}, delete_files={delete_files}")
            
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return False
            
            # Get name for logging
            torrent_name = "Unknown"
            try:
                if handle.has_metadata():
                    torrent_name = handle.get_torrent_info().name()
            except Exception:
                pass
            
            # Remove from session
            self.session.remove_torrent(handle, int(delete_files))
            
            # Remove from dictionary
            self.torrents.pop(info_hash, None)
            
            # Remove from database
            self.db_manager.remove_torrent(info_hash)
            
            logger.info(f"Torrent '{torrent_name}' removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error removing torrent: {str(e)}", exc_info=True)
            return False
    
    def pause_torrent(self, info_hash: str) -> bool:
        """Pause a torrent.
        
        Args:
            info_hash: The info hash of the torrent to pause
            
        Returns:
            True if the torrent was paused successfully, False otherwise
        """
        try:
            logger.info(f"Pausing torrent with hash: {info_hash}")
            
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return False
            
            # Pause torrent
            handle.pause()
            
            # Update in database
            self.db_manager.update_torrent_status(info_hash, "paused")
            
            logger.info(f"Torrent paused successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error pausing torrent: {str(e)}", exc_info=True)
            return False
    
    def resume_torrent(self, info_hash: str) -> bool:
        """Resume a paused torrent.
        
        Args:
            info_hash: The info hash of the torrent to resume
            
        Returns:
            True if the torrent was resumed successfully, False otherwise
        """
        try:
            logger.info(f"Resuming torrent with hash: {info_hash}")
            
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return False
            
            # Resume torrent
            handle.resume()
            
            # Update in database
            self.db_manager.update_torrent_status(info_hash, "downloading")
            
            logger.info(f"Torrent resumed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resuming torrent: {str(e)}", exc_info=True)
            return False
    
    def set_torrent_priority(self, info_hash: str, priority: int) -> bool:
        """Set the priority of a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            priority: The priority value (0-7, where 7 is highest)
            
        Returns:
            True if the priority was set successfully, False otherwise
        """
        try:
            logger.info(f"Setting priority {priority} for torrent with hash: {info_hash}")
            
            # Validate priority
            if priority < 0 or priority > 7:
                logger.warning(f"Invalid priority value: {priority}")
                return False
            
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return False
            
            # Set priority
            handle.set_priority(priority)
            
            logger.info(f"Torrent priority set successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting torrent priority: {str(e)}", exc_info=True)
            return False
    
    def set_file_priorities(self, info_hash: str, file_priorities: Dict[int, int]) -> bool:
        """Set the priorities of individual files in a torrent.
        
        Args:
            info_hash: The info hash of the torrent
            file_priorities: Dictionary mapping file indices to priority values
            
        Returns:
            True if the priorities were set successfully, False otherwise
        """
        try:
            logger.info(f"Setting file priorities for torrent with hash: {info_hash}")
            
            # Get torrent handle
            handle = self._get_handle(info_hash)
            if not handle:
                logger.warning(f"Torrent not found with hash: {info_hash}")
                return False
            
            # Check if we have metadata
            if not handle.has_metadata():
                logger.warning(f"Torrent doesn't have metadata yet: {info_hash}")
                return False
            
            # Get torrent info
            info = handle.get_torrent_info()
            num_files = info.num_files()
            
            # Create priority list for all files
            file_prio = handle.file_priorities()
            
            # Update priorities
            for file_index, priority in file_priorities.items():
                if 0 <= file_index < num_files and 0 <= priority <= 7:
                    file_prio[file_index] = priority
            
            # Set priorities
            handle.prioritize_files(file_prio)
            
            logger.info(f"File priorities set successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting file priorities: {str(e)}", exc_info=True)
            return False
    
    def _get_handle(self, info_hash: str) -> Optional[lt.torrent_handle]:
        """Get torrent handle by info hash.
        
        Args:
            info_hash: The info hash of the torrent
            
        Returns:
            Torrent handle if found, None otherwise
        """
        # Try to get from internal dictionary first
        handle = self.torrents.get(info_hash)
        if handle:
            return handle
        
        # Try to find in session
        try:
            sha1_hash = lt.sha1_hash(bytes.fromhex(info_hash))
            handle = self.session.find_torrent(sha1_hash)
            if handle.is_valid():
                # Add to dictionary for future lookups
                self.torrents[info_hash] = handle
                return handle
        except Exception as e:
            logger.error(f"Error getting handle for {info_hash}: {e}")
        
        return None
    
    def _add_to_database(self, handle: lt.torrent_handle, source: str, save_path: str) -> None:
        """Add torrent to database.
        
        Args:
            handle: Torrent handle
            source: Source of the torrent (magnet link or file path)
            save_path: Save path for the torrent
        """
        try:
            info_hash = str(handle.info_hash()).lower()
            
            if handle.has_metadata():
                info = handle.get_torrent_info()
                name = info.name()
                size = info.total_size()
                
                # Add torrent to database
                self.db_manager.add_torrent(
                    name=name,
                    magnet_link=source,
                    info_hash=info_hash,
                    size=size,
                    save_path=save_path
                )
                
                # Add files to database
                files = []
                for i in range(info.num_files()):
                    file_entry = info.files().at(i)
                    files.append({
                        'name': file_entry.path,
                        'size': file_entry.size
                    })
                
                # Add files to database
                self.db_manager.add_torrent_files(info_hash, files)
                
                logger.info(f"Added torrent to database with metadata: {name}")
            else:
                # Add torrent with minimal information
                name = os.path.basename(source) if os.path.isfile(source) else "Unknown"
                self.db_manager.add_torrent(
                    name=name,
                    magnet_link=source,
                    info_hash=info_hash,
                    size=0,
                    save_path=save_path
                )
                logger.info(f"Added torrent to database without metadata: {name}")
            
        except Exception as e:
            logger.error(f"Error adding torrent to database: {e}", exc_info=True) 