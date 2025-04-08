import libtorrent as lt
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

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
        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.torrents: Dict[str, lt.torrent_handle] = {}
        self.save_path = save_path
        
    def add_torrent(self, magnet_link: str) -> Optional[str]:
        """Add a new torrent from magnet link."""
        try:
            params = lt.parse_magnet_uri(magnet_link)
            params.save_path = self.save_path
            handle = self.session.add_torrent(params)
            self.torrents[handle.info_hash().to_string()] = handle
            return handle.info_hash().to_string()
        except Exception as e:
            print(f"Error adding torrent: {e}")
            return None
            
    def remove_torrent(self, torrent_hash: str, delete_files: bool = False):
        """Remove a torrent from the session."""
        if torrent_hash in self.torrents:
            self.session.remove_torrent(self.torrents[torrent_hash], int(delete_files))
            del self.torrents[torrent_hash]
            
    def pause_torrent(self, torrent_hash: str):
        """Pause a torrent."""
        if torrent_hash in self.torrents:
            self.torrents[torrent_hash].pause()
            
    def resume_torrent(self, torrent_hash: str):
        """Resume a torrent."""
        if torrent_hash in self.torrents:
            self.torrents[torrent_hash].resume()
            
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
        """Get information about all torrents."""
        return [self.get_torrent_info(hash) for hash in self.torrents.keys()]
        
    def set_save_path(self, path: str):
        """Set the default save path for new torrents."""
        self.save_path = path
        for handle in self.torrents.values():
            handle.move_storage(path) 