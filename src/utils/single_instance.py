"""Single-instance guard + CLI handoff via QLocalSocket / QLocalServer.

When the user double-clicks a magnet or .torrent file and a Yoink window
is already running, we want to hand the path off to the existing process
instead of launching a second one. This module exposes:

* ``send_to_existing(payload)`` — call before booting anything; returns
  True if another instance accepted the payload.
* ``listen(callback)`` — start a local server that invokes ``callback``
  with each incoming payload string.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from utils.logger import setup_logger

logger = setup_logger("utils.single_instance")

_SOCKET_NAME = "yoink-cli-handoff"


def send_to_existing(payload: str, timeout_ms: int = 500) -> bool:
    """Try to deliver ``payload`` to an existing Yoink. True on success."""
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
    """QLocalServer wrapper that emits each received CLI payload."""

    payloadReceived = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        # Strip a stale socket file (Linux/macOS only; harmless on Windows).
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
    """Start listening for handoff payloads and invoke ``callback`` per message."""
    server = CliHandoffServer()
    server.payloadReceived.connect(callback)
    return server
