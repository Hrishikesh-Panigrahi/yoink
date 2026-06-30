"""Torrent lifecycle slots: add, pause, resume, remove, file selection, labels."""

from __future__ import annotations

import base64
import json
import os
import tempfile

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

import db
import torrents
from utils.logger import setup_logger

logger = setup_logger("bridge.torrents")


class TorrentsMixin:
    """Mixin providing torrent-related QWebChannel slots."""

    @pyqtSlot(result=str)
    def getDownloads(self) -> str:
        """Return a snapshot of current downloads as JSON."""
        try:
            payload = [s.to_dict() for s in torrents.list_torrents(self.session)]
            return json.dumps(payload)
        except Exception as exc:
            logger.error(f"getDownloads error: {exc}")
            return "[]"

    @pyqtSlot(str, result=str)
    def addTorrent(self, magnet: str) -> str:
        """Add a torrent from a magnet link. Returns JSON with hash and duplicate flag."""
        magnet = (magnet or "").strip()
        if not magnet:
            self.toast.emit("error", "No magnet link provided")
            return json.dumps({"hash": "", "wasExisting": False})
        try:
            torrents.set_save_path(self.session, self.save_folder)
            info_hash, was_existing = torrents.add_magnet_verbose(self.session, magnet)
            if was_existing:
                self.toast.emit("info", "Already in your library")
            else:
                self.toast.emit("success", "Torrent added")
            return json.dumps({"hash": info_hash, "wasExisting": was_existing})
        except Exception as exc:
            logger.exception("addTorrent failed")
            self.toast.emit("error", f"Failed to add torrent: {exc}")
            return json.dumps({"hash": "", "wasExisting": False})

    @pyqtSlot(str, str, result=str)
    def addTorrentFromBytes(self, name: str, base64_payload: str) -> str:
        """Add a .torrent dragged in from the browser. ``base64_payload`` is base64-encoded."""
        try:
            raw = base64.b64decode(base64_payload or "", validate=False)
            if not raw:
                self.toast.emit("error", "Empty .torrent payload")
                return json.dumps({"hash": "", "wasExisting": False})
            safe_name = os.path.basename(name or "dropped.torrent")
            with tempfile.NamedTemporaryFile(
                prefix="yoink-drop-", suffix=".torrent", delete=False
            ) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            torrents.set_save_path(self.session, self.save_folder)
            info_hash = torrents.add_torrent_file(self.session, tmp_path)
            self.toast.emit("success", f"Added: {safe_name}")
            return json.dumps({"hash": info_hash, "wasExisting": False, "name": safe_name})
        except Exception as exc:
            logger.exception("addTorrentFromBytes failed")
            self.toast.emit("error", f"Could not add .torrent: {exc}")
            return json.dumps({"hash": "", "wasExisting": False})

    @pyqtSlot(result=str)
    def pickAndAddTorrentFile(self) -> str:
        """Open a native file picker and add the selected .torrent file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Select Torrent File",
                self.save_folder,
                "Torrent Files (*.torrent);;All Files (*)",
            )
            if not file_path:
                return ""
            torrents.set_save_path(self.session, self.save_folder)
            info_hash = torrents.add_torrent_file(self.session, file_path)
            self.toast.emit("success", f"Added: {os.path.basename(file_path)}")
            return info_hash
        except Exception as exc:
            logger.exception("pickAndAddTorrentFile failed")
            self.toast.emit("error", str(exc))
            return ""

    @pyqtSlot(str, result=bool)
    def pauseTorrent(self, info_hash: str) -> bool:
        try:
            return torrents.pause(self.session, info_hash)
        except Exception as exc:
            logger.exception("pauseTorrent failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(str, result=bool)
    def resumeTorrent(self, info_hash: str) -> bool:
        try:
            return torrents.resume(self.session, info_hash)
        except Exception as exc:
            logger.exception("resumeTorrent failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(result=int)
    def pauseAll(self) -> int:
        """Pause every torrent. Returns how many were paused."""
        try:
            count = torrents.pause_all(self.session)
            if count:
                self.toast.emit("success", f"Paused {count} torrent{'s' if count != 1 else ''}")
            return count
        except Exception as exc:
            logger.exception("pauseAll failed")
            self.toast.emit("error", str(exc))
            return 0

    @pyqtSlot(result=int)
    def resumeAll(self) -> int:
        """Resume every torrent. Returns how many were resumed."""
        try:
            count = torrents.resume_all(self.session)
            if count:
                self.toast.emit("success", f"Resumed {count} torrent{'s' if count != 1 else ''}")
            return count
        except Exception as exc:
            logger.exception("resumeAll failed")
            self.toast.emit("error", str(exc))
            return 0

    @pyqtSlot(str, result=str)
    def getTorrentFiles(self, info_hash: str) -> str:
        """Return the per-file table for a torrent (empty list while metadata loads)."""
        try:
            files = torrents.list_files(self.session, info_hash)
            return json.dumps([f.to_dict() for f in files])
        except Exception as exc:
            logger.error(f"getTorrentFiles failed: {exc}")
            return "[]"

    @pyqtSlot(str, str, result=bool)
    def setFilePriorities(self, info_hash: str, priorities_json: str) -> bool:
        """Apply a {index: priority} map. Priority: 0=skip, 1=low, 4=normal, 7=high."""
        try:
            payload = json.loads(priorities_json or "{}")
            if not isinstance(payload, dict):
                return False
            ok = torrents.set_file_priorities(self.session, info_hash, payload)
            if ok:
                self.toast.emit("success", "File selection updated")
            return ok
        except Exception as exc:
            logger.exception("setFilePriorities failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(str, bool, result=bool)
    def removeTorrent(self, info_hash: str, delete_files: bool) -> bool:
        try:
            ok = torrents.remove(self.session, info_hash, delete_files)
            if ok:
                self.toast.emit("success", "Removed")
            return ok
        except Exception as exc:
            logger.exception("removeTorrent failed")
            self.toast.emit("error", str(exc))
            return False

    @pyqtSlot(str, result=str)
    def getDownloadFile(self, info_hash: str) -> str:
        """Return the absolute path of the largest file in a completed torrent."""
        try:
            handle = self.session.handles.get((info_hash or "").lower())
            if handle is None or not handle.is_valid():
                return ""
            try:
                has_meta = handle.has_metadata()
            except Exception:
                has_meta = bool(handle.status().has_metadata)
            if not has_meta:
                return ""
            info = handle.get_torrent_info()
            save_path = handle.status().save_path
            files = info.files()
            best_idx = 0
            best_size = -1
            for idx in range(files.num_files()):
                size = files.file_size(idx)
                if size > best_size:
                    best_size = size
                    best_idx = idx
            return os.path.join(save_path, files.file_path(best_idx))
        except Exception as exc:
            logger.error(f"getDownloadFile failed: {exc}")
            return ""

    @pyqtSlot(str, result=str)
    def pickAndMoveTorrent(self, info_hash: str) -> str:
        """Pick a new save folder for a single torrent and move its data there."""
        info_hash = (info_hash or "").lower()
        handle = self.session.handles.get(info_hash)
        if handle is None or not handle.is_valid():
            self.toast.emit("error", "Torrent not found")
            return ""
        try:
            current = handle.status().save_path
            new_dir = QFileDialog.getExistingDirectory(
                None,
                "Move torrent to...",
                current or self.save_folder,
                QFileDialog.Option.ShowDirsOnly,
            )
            if not new_dir:
                return ""
            handle.move_storage(new_dir)
            db.save_torrent(
                info_hash=info_hash,
                name=handle.status().name or info_hash,
                magnet_link="",
                save_path=new_dir,
            )
            self.toast.emit("success", f"Moving files to {new_dir}")
            return new_dir
        except Exception as exc:
            logger.exception("pickAndMoveTorrent failed")
            self.toast.emit("error", str(exc))
            return ""

    @pyqtSlot(str, result=str)
    def getLabels(self, info_hash: str) -> str:
        raw = db.get_setting(f"labels.{(info_hash or '').lower()}") or ""
        return json.dumps([part for part in raw.split(",") if part])

    @pyqtSlot(str, str)
    def setLabels(self, info_hash: str, labels_json: str) -> None:
        try:
            labels = json.loads(labels_json or "[]")
            if not isinstance(labels, list):
                return
            cleaned = sorted({str(x).strip() for x in labels if str(x).strip()})
            db.set_setting(f"labels.{(info_hash or '').lower()}", ",".join(cleaned))
        except Exception as exc:
            logger.error(f"setLabels failed: {exc}")

    @pyqtSlot(result=str)
    def getAllLabels(self) -> str:
        """Return the union of all labels currently in use."""
        all_settings = db.get_all_settings()
        labels = set()
        for key, value in all_settings.items():
            if key.startswith("labels.") and value:
                labels.update(part for part in value.split(",") if part)
        return json.dumps(sorted(labels))
