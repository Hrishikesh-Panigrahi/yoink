"""The in-app video window: a native surface for libvlc plus transport controls.

The window takes a `buffer_probe` callable so it can show buffering progress
without knowing anything about torrents.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from player.backend import VlcPlayer
from utils.logger import setup_logger

logger = setup_logger("player.window")

TICK_MS = 500

#: Keys read from the stream-status dict that `buffer_probe` returns.
_READY_KEY = "ready"
_PROGRESS_KEY = "bufferProgress"


def format_time(milliseconds: int) -> str:
    """`h:mm:ss` from one hour up, `m:ss` below that, `--:--` if unknown."""
    if milliseconds is None or milliseconds < 0:
        return "--:--"
    total_seconds = int(milliseconds // 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class PlayerWindow(QMainWindow):
    def __init__(
        self,
        player: VlcPlayer,
        buffer_probe: Optional[Callable[[], dict]] = None,
        on_close: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._buffer_probe = buffer_probe
        self._on_close = on_close
        self._scrubbing = False

        self.setWindowTitle("Yoink Player")
        self.resize(960, 600)
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.surface = QFrame(root)
        self.surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.surface.setAutoFillBackground(True)
        palette = self.surface.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.surface.setPalette(palette)
        self.surface.setMinimumHeight(240)
        layout.addWidget(self.surface, stretch=1)

        layout.addWidget(self._build_controls(root))
        self.setCentralWidget(root)

    def _build_controls(self, parent: QWidget) -> QWidget:
        bar = QWidget(parent)
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 8, 10, 10)
        row.setSpacing(10)

        self.play_button = QPushButton("Pause", bar)
        self.play_button.setFixedWidth(80)
        self.play_button.clicked.connect(self.toggle_play)
        row.addWidget(self.play_button)

        self.elapsed_label = QLabel("--:--", bar)
        row.addWidget(self.elapsed_label)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal, bar)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_scrub_start)
        self.seek_slider.sliderReleased.connect(self._on_scrub_end)
        row.addWidget(self.seek_slider, stretch=1)

        self.duration_label = QLabel("--:--", bar)
        row.addWidget(self.duration_label)

        self.buffer_label = QLabel("", bar)
        self.buffer_label.setMinimumWidth(110)
        row.addWidget(self.buffer_label)

        volume = QSlider(Qt.Orientation.Horizontal, bar)
        volume.setRange(0, 100)
        volume.setFixedWidth(110)
        volume.setValue(80)
        volume.valueChanged.connect(self._player.set_volume)
        row.addWidget(volume)

        return bar

    def open(self, path: str, title: str = "", expected_size: int = 0) -> None:
        """Show the window and start playing `path`.

        `expected_size` is the file's final length. It lets playback wait for
        bytes that are still downloading instead of stopping early.
        """
        self.setWindowTitle(f"Yoink Player: {title or os.path.basename(path)}")
        self.show()
        self.raise_()
        self.activateWindow()
        # The surface has to exist natively before libvlc can draw into it.
        self._player.attach(int(self.surface.winId()))
        self._player.set_volume(80)
        self._player.play(path, expected_size)
        self._timer.start()
        self._tick()

    def toggle_play(self) -> None:
        if self._player.is_playing():
            self._player.pause()
            self.play_button.setText("Play")
        else:
            self._player.play()
            self.play_button.setText("Pause")

    def closeEvent(self, event) -> None:
        self._timer.stop()
        try:
            self._player.stop()
            self._player.release()
        except Exception as exc:
            logger.error(f"Player teardown failed: {exc}")
        if self._on_close is not None:
            try:
                self._on_close()
            except Exception as exc:
                logger.error(f"Player close callback failed: {exc}")
        super().closeEvent(event)

    def _on_scrub_start(self) -> None:
        self._scrubbing = True

    def _on_scrub_end(self) -> None:
        self._scrubbing = False
        self._player.seek_ms(self.seek_slider.value())

    def _tick(self) -> None:
        # Re-read every tick, because VLC reports a growing length for a file
        # that is still downloading.
        duration = self._player.duration_ms()
        elapsed = self._player.time_ms()

        if duration > 0 and not self._scrubbing:
            self.seek_slider.setRange(0, duration)
            self.seek_slider.setValue(max(0, elapsed))
        self.elapsed_label.setText(format_time(elapsed))
        self.duration_label.setText(format_time(duration))
        self.play_button.setText("Pause" if self._player.is_playing() else "Play")
        self.buffer_label.setText(self._buffer_text())

    def _buffer_text(self) -> str:
        if self._buffer_probe is None:
            return ""
        try:
            status = self._buffer_probe() or {}
        except Exception as exc:
            logger.debug(f"buffer probe failed: {exc}")
            return ""
        if not status:
            return ""
        if status.get(_READY_KEY):
            return "Buffered"
        percent = float(status.get(_PROGRESS_KEY) or 0.0)
        return f"Buffering {percent:.0f}%"
