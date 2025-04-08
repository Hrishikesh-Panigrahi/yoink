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
    """Data class to store torrent information"""
    name: str
    size: str
    seeds: int
    peers: int
    upload_date: str
    status: str
    hash: str

class TorrentManager:
    def __init__(self):
        logger.info("Initializing TorrentManager")
        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.torrents = {}
        self.save_path = os.path.expanduser("~/Downloads")
        logger.info(f"Save path set to: {self.save_path}")

    def add_torrent(self, magnet_link: str) -> bool:
        """Add a new torrent from magnet link"""
        try:
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = self.save_path
            handle = self.session.add_torrent(params)
            self.torrents[handle.info_hash().to_string()] = handle
            logger.info(f"Added torrent: {handle.name()}")
            return True
        except Exception as e:
            logger.error(f"Error adding torrent: {str(e)}")
            return False

    def remove_torrent(self, name: str, delete_files: bool = False) -> bool:
        """Remove a torrent by name"""
        try:
            for handle in self.torrents.values():
                if handle.name() == name:
                    self.session.remove_torrent(handle, delete_files)
                    logger.info(f"Removed torrent: {name}")
                    return True
            logger.warning(f"Torrent not found: {name}")
            return False
        except Exception as e:
            logger.error(f"Error removing torrent: {str(e)}")
            return False

    def pause_torrent(self, name: str) -> bool:
        """Pause a torrent by name"""
        try:
            for handle in self.torrents.values():
                if handle.name() == name:
                    handle.pause()
                    logger.info(f"Paused torrent: {name}")
                    return True
            logger.warning(f"Torrent not found: {name}")
            return False
        except Exception as e:
            logger.error(f"Error pausing torrent: {str(e)}")
            return False

    def resume_torrent(self, name: str) -> bool:
        """Resume a torrent by name"""
        try:
            for handle in self.torrents.values():
                if handle.name() == name:
                    handle.resume()
                    logger.info(f"Resumed torrent: {name}")
                    return True
            logger.warning(f"Torrent not found: {name}")
            return False
        except Exception as e:
            logger.error(f"Error resuming torrent: {str(e)}")
            return False

    def get_torrents(self) -> List[TorrentInfo]:
        """Get information about all torrents"""
        try:
            results = []
            for handle in self.torrents.values():
                try:
                    status = handle.status()
                    info = handle.get_torrent_info()
                    
                    # Get torrent state
                    state_str = "Unknown"
                    if status.paused:
                        state_str = "Paused"
                    elif status.errc:
                        state_str = "Error"
                    elif status.is_seeding:
                        state_str = "Seeding"
                    elif status.is_downloading:
                        state_str = "Downloading"
                    elif status.is_finished:
                        state_str = "Finished"
                        
                    # Format size
                    size_bytes = info.total_size()
                    size_str = self._format_size(size_bytes)
                    
                    # Get upload date
                    upload_date = datetime.fromtimestamp(info.creation_date()).strftime('%Y-%m-%d %H:%M:%S')
                    
                    results.append(TorrentInfo(
                        name=handle.name(),
                        size=size_str,
                        seeds=status.num_seeds,
                        peers=status.num_peers,
                        upload_date=upload_date,
                        status=state_str,
                        hash=handle.info_hash().to_string()
                    ))
                except Exception as e:
                    logger.error(f"Error getting torrent info: {str(e)}")
                    continue
                    
            return results
        except Exception as e:
            logger.error(f"Error getting torrents: {str(e)}")
            return []

    def _format_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

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