"""Passes a magnet link or .torrent path from a second launch to the Yoink that is
already running, over a local socket, so only one copy runs.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from utils.logger import setup_logger

logger = setup_logger("utils.single_instance")

_SOCKET_NAME = "yoink-cli-handoff"


def send_to_existing(payload: str, timeout_ms: int = 500) -> bool:
    """Return True if a running Yoink received `payload`.

    Call it before this process starts its own handoff server.
    """
    socket = QLocalSocket()
    socket.connectToServer(_SOCKET_NAME)
    if not socket.waitForConnected(timeout_ms):
        return False
    try:
        data = (payload or "").encode("utf-8")
        socket.write(data)
        socket.flush()
        socket.waitForBytesWritten(timeout_ms)
        return True
    finally:
        socket.disconnectFromServer()


class CliHandoffServer(QObject):
    payloadReceived = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        # Removes a stale socket file left by an earlier run (Linux and macOS only).
        QLocalServer.removeServer(_SOCKET_NAME)
        if not self._server.listen(_SOCKET_NAME):
            logger.warning(f"CLI handoff server failed to listen: {self._server.errorString()}")
        else:
            self._server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.readyRead.connect(lambda: self._on_ready_read(socket))
        socket.disconnected.connect(socket.deleteLater)

    def _on_ready_read(self, socket: QLocalSocket) -> None:
        try:
            raw = bytes(socket.readAll())
            payload = raw.decode("utf-8", errors="replace")
            if payload:
                self.payloadReceived.emit(payload)
        except Exception as exc:
            logger.error(f"CLI handoff read failed: {exc}")


def listen(callback: Callable[[str], None]) -> CliHandoffServer:
    server = CliHandoffServer()
    server.payloadReceived.connect(callback)
    return server
