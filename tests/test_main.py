"""Tests for the helpers in `src/main.py`.

`main()` itself builds a QApplication and a window, so only the helpers around
it are tested here.
"""

from __future__ import annotations

import sys

import pytest

import main


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["yoink.exe"], ""),
        (["yoink.exe", "--minimized"], ""),
        (["yoink.exe", "magnet:?xt=urn:btih:" + "a" * 40], "magnet:?xt=urn:btih:" + "a" * 40),
        (["yoink.exe", r"C:\downloads\Ubuntu.TORRENT"], r"C:\downloads\Ubuntu.TORRENT"),
        (["yoink.exe", "--minimized", "magnet:?xt=urn:btih:b"], "magnet:?xt=urn:btih:b"),
    ],
)
def test_extract_payload(argv, expected):
    assert main._extract_payload(argv) == expected


def test_extract_payload_ignores_the_program_name():
    assert main._extract_payload([r"C:\apps\yoink.torrent"]) == ""


def test_installing_the_hook_replaces_the_default(monkeypatch):
    """PyQt aborts on an unhandled exception only while the hook is `sys.__excepthook__`."""
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)

    main._install_exception_logger()

    assert sys.excepthook is main._log_unhandled
    assert sys.excepthook is not sys.__excepthook__


def test_the_hook_logs_the_whole_traceback(monkeypatch):
    logged: list[str] = []
    monkeypatch.setattr(main.logger, "critical", logged.append)

    try:
        raise ValueError("kaboom from a slot")
    except ValueError:
        main._log_unhandled(*sys.exc_info())

    assert len(logged) == 1
    assert "ValueError: kaboom from a slot" in logged[0]
    assert "Traceback (most recent call last)" in logged[0]


def test_the_hook_does_not_raise_out_of_itself(monkeypatch):
    monkeypatch.setattr(main.logger, "critical", lambda _msg: None)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        main._log_unhandled(*sys.exc_info())


def test_keyboard_interrupt_still_reaches_the_default_hook(monkeypatch):
    logged: list[str] = []
    forwarded: list[tuple] = []
    monkeypatch.setattr(main.logger, "critical", logged.append)
    monkeypatch.setattr(sys, "__excepthook__", lambda *info: forwarded.append(info))

    try:
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        main._log_unhandled(*sys.exc_info())

    assert logged == []
    assert len(forwarded) == 1
