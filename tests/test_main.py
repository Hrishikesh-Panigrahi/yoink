"""Tests for the entrypoint helpers in `src/main.py`.

`main()` itself builds a QApplication and a window, which a unit test does not
want, so only the pieces around it are covered here. The exception hook is the
one that matters: without it an exception escaping any slot aborts the process
with no traceback and no log line at all.
"""

from __future__ import annotations

import sys

import pytest

import main

# ----- CLI payload --------------------------------------------------------


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
    """argv[0] can be a .torrent-looking path; it is never the payload."""
    assert main._extract_payload([r"C:\apps\yoink.torrent"]) == ""


# ----- Unhandled exception hook -------------------------------------------


def test_installing_the_hook_replaces_the_default(monkeypatch):
    """PyQt only aborts when the hook is still `sys.__excepthook__`."""
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
    """It runs where nothing can catch it, so it must not throw."""
    monkeypatch.setattr(main.logger, "critical", lambda _msg: None)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        main._log_unhandled(*sys.exc_info())


def test_keyboard_interrupt_still_reaches_the_default_hook(monkeypatch):
    """Ctrl-C should keep quitting rather than being logged and swallowed."""
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
