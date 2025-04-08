import libtorrent as lt
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from utils.logger import setup_logger

# Set up logger
logger = setup_logger('torrent_manager')

@dataclass
class TorrentInfo:
    name: str
    size: int
    progress: float
    download_rate: int
    upload_rate: int
    num_peers: int
    num_seeds: int
    state: str
    save_path: str
    files: List[Dict]

class TorrentManager:
    def __init__(self, save_path: str = os.path.expanduser("~/Downloads")):
        logger.info("Initializing TorrentManager")
        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.torrents: Dict[str, lt.torrent_handle] = {}
        self.save_path = save_path
        logger.info(f"Save path set to: {self.save_path}")
        
    def add_torrent(self, magnet_link: str) -> bool:
        try:
            logger.info(f"Adding torrent from magnet link: {magnet_link[:50]}...")
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = self.save_path
            
            handle = self.session.add_torrent(params)
            self.torrents[handle.info_hash().to_string()] = handle
            logger.info(f"Torrent added successfully: {handle.name()}")
            return True
        except Exception as e:
            logger.error(f"Failed to add torrent: {str(e)}", exc_info=True)
            return False
            
    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        try:
            logger.info(f"Removing torrent with hash: {torrent_hash}")
            if torrent_hash in self.torrents:
                self.session.remove_torrent(self.torrents[torrent_hash], int(delete_files))
                del self.torrents[torrent_hash]
                logger.info(f"Torrent removed successfully: {self.torrents[torrent_hash].name()}")
                return True
            logger.warning(f"Torrent not found with hash: {torrent_hash}")
            return False
        except Exception as e:
            logger.error(f"Failed to remove torrent: {str(e)}", exc_info=True)
            return False
            
    def pause_torrent(self, torrent_hash: str) -> bool:
        try:
            logger.info(f"Pausing torrent with hash: {torrent_hash}")
            if torrent_hash in self.torrents:
                self.torrents[torrent_hash].pause()
                logger.info(f"Torrent paused successfully: {self.torrents[torrent_hash].name()}")
                return True
            logger.warning(f"Torrent not found with hash: {torrent_hash}")
            return False
        except Exception as e:
            logger.error(f"Failed to pause torrent: {str(e)}", exc_info=True)
            return False
            
    def resume_torrent(self, torrent_hash: str) -> bool:
        try:
            logger.info(f"Resuming torrent with hash: {torrent_hash}")
            if torrent_hash in self.torrents:
                self.torrents[torrent_hash].resume()
                logger.info(f"Torrent resumed successfully: {self.torrents[torrent_hash].name()}")
                return True
            logger.warning(f"Torrent not found with hash: {torrent_hash}")
            return False
        except Exception as e:
            logger.error(f"Failed to resume torrent: {str(e)}", exc_info=True)
            return False
            
    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """Get information about a specific torrent."""
        if torrent_hash not in self.torrents:
            return None
            
        handle = self.torrents[torrent_hash]
        status = handle.status()
        
        files = []
        if handle.has_metadata():
            for i, f in enumerate(handle.get_torrent_info().files()):
                files.append({
                    'name': f.path,
                    'size': f.size,
                    'progress': handle.file_progress(i) / f.size * 100
                })
        
        return TorrentInfo(
            name=status.name,
            size=status.total_wanted,
            progress=status.progress * 100,
            download_rate=status.download_rate,
            upload_rate=status.upload_rate,
            num_peers=status.num_peers,
            num_seeds=status.num_seeds,
            state=str(status.state),
            save_path=status.save_path,
            files=files
        )
        
    def get_all_torrents(self) -> List[TorrentInfo]:
        try:
            logger.debug("Getting all torrents")
            torrent_info_list = []
            
            for handle in self.torrents.values():
                try:
                    status = handle.status()
                    info = handle.get_torrent_info()
                    
                    if info:
                        torrent_info = TorrentInfo(
                            name=info.name(),
                            size=info.total_size(),
                            progress=status.progress * 100,
                            download_rate=status.download_rate,
                            upload_rate=status.upload_rate,
                            num_peers=status.num_peers,
                            num_seeds=status.num_seeds,
                            state=self._get_state_string(status.state),
                            save_path=status.save_path,
                            files=[]
                        )
                        torrent_info_list.append(torrent_info)
                except Exception as e:
                    logger.error(f"Error getting info for torrent: {str(e)}", exc_info=True)
                    continue
                    
            logger.debug(f"Found {len(torrent_info_list)} active torrents")
            return torrent_info_list
        except Exception as e:
            logger.error(f"Error getting torrent list: {str(e)}", exc_info=True)
            return []
            
    def _get_state_string(self, state: int) -> str:
        state_map = {
            lt.torrent_status.checking_files: "Checking",
            lt.torrent_status.downloading_metadata: "Downloading Metadata",
            lt.torrent_status.downloading: "Downloading",
            lt.torrent_status.finished: "Finished",
            lt.torrent_status.seeding: "Seeding",
            lt.torrent_status.allocating: "Allocating",
            lt.torrent_status.checking_resume_data: "Checking Resume Data"
        }
        return state_map.get(state, "Unknown")
        
    def set_save_path(self, path: str):
        """Set the default save path for new torrents."""
        self.save_path = path
        for handle in self.torrents.values():
            handle.move_storage(path) 