"""Tests for `src/player/`.

No libvlc is installed on a CI runner, and that is the interesting case: the
whole point of `player.runtime` is that a missing runtime produces a reason
rather than an exception at import time. Discovery is driven against temporary
directories shaped like a real VLC install, so it is tested without one.

Actual video decoding is not covered here — that needs a real library, a real
window and a real file.
"""

from __future__ import annotations

import ctypes
import threading
import time

import pytest

from player import backend, runtime, source
from player.window import format_time


@pytest.fixture(autouse=True)
def clear_runtime_cache():
    """`load_vlc` caches its outcome; tests must not inherit each other's."""
    runtime.reset_cache()
    yield
    runtime.reset_cache()


def make_vlc_dir(root, name="VLC", library="libvlc.dll", plugins=True):
    """Build a directory that looks like an installed VLC."""
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    if library:
        (directory / library).write_bytes(b"not really a dll")
    if plugins:
        (directory / "plugins").mkdir(exist_ok=True)
    return directory


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(runtime.sys, "platform", "win32")


@pytest.fixture(autouse=True)
def no_real_vlc(monkeypatch):
    """Ignore any VLC actually installed on the machine running these tests."""
    monkeypatch.setattr(runtime, "_data_dir", lambda: None)
    monkeypatch.setattr(runtime, "_registry_dirs", list)
    monkeypatch.setattr(runtime, "_WINDOWS_INSTALL_DIRS", ())


# ----- Discovery ----------------------------------------------------------


def test_env_var_points_at_a_runtime(monkeypatch, tmp_path, windows):
    directory = make_vlc_dir(tmp_path)
    monkeypatch.setenv(runtime.DIR_ENV_VAR, str(directory))
    monkeypatch.setattr(runtime, "_registry_dirs", list)

    found = runtime.find_runtime()

    assert found is not None
    assert found.directory == directory
    assert found.plugin_path == directory / "plugins"
    assert found.source == runtime.DIR_ENV_VAR


def test_env_var_wins_over_an_installed_copy(monkeypatch, tmp_path, windows):
    preferred = make_vlc_dir(tmp_path, "portable")
    installed = make_vlc_dir(tmp_path, "installed")
    monkeypatch.setenv(runtime.DIR_ENV_VAR, str(preferred))
    monkeypatch.setattr(runtime, "_registry_dirs", lambda: [installed])

    assert runtime.find_runtime().directory == preferred


def test_registry_is_used_when_the_env_var_is_unset(monkeypatch, tmp_path, windows):
    installed = make_vlc_dir(tmp_path)
    monkeypatch.delenv(runtime.DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(runtime, "_registry_dirs", lambda: [installed])

    found = runtime.find_runtime()

    assert found.directory == installed
    assert found.source == "registry"


def test_a_bundled_runtime_is_preferred_over_an_installed_one(monkeypatch, tmp_path, windows):
    bundled = make_vlc_dir(tmp_path, "bundled")
    installed = make_vlc_dir(tmp_path, "installed")
    monkeypatch.delenv(runtime.DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(runtime, "_bundled_dir", lambda: bundled)
    monkeypatch.setattr(runtime, "_registry_dirs", lambda: [installed])

    found = runtime.find_runtime()

    assert found.directory == bundled
    assert found.source == "bundled"


def test_a_directory_without_the_library_is_rejected(monkeypatch, tmp_path, windows):
    broken = make_vlc_dir(tmp_path, "no-dll", library="")
    monkeypatch.setenv(runtime.DIR_ENV_VAR, str(broken))
    monkeypatch.setattr(runtime, "_registry_dirs", list)
    monkeypatch.setattr(runtime, "_WINDOWS_INSTALL_DIRS", ())

    assert runtime.find_runtime() is None


def test_a_directory_without_plugins_is_rejected(monkeypatch, tmp_path, windows):
    # libvlc loads but decodes nothing without its plugin tree, so half an
    # install is worse than none: it would fail at playback instead of startup.
    broken = make_vlc_dir(tmp_path, "no-plugins", plugins=False)
    monkeypatch.setenv(runtime.DIR_ENV_VAR, str(broken))
    monkeypatch.setattr(runtime, "_registry_dirs", list)
    monkeypatch.setattr(runtime, "_WINDOWS_INSTALL_DIRS", ())

    assert runtime.find_runtime() is None


def test_a_missing_directory_is_rejected(monkeypatch, tmp_path, windows):
    monkeypatch.setenv(runtime.DIR_ENV_VAR, str(tmp_path / "nope"))
    monkeypatch.setattr(runtime, "_registry_dirs", list)
    monkeypatch.setattr(runtime, "_WINDOWS_INSTALL_DIRS", ())

    assert runtime.find_runtime() is None


def test_bundled_dir_is_only_consulted_in_a_frozen_build(monkeypatch):
    monkeypatch.delattr(runtime.sys, "frozen", raising=False)

    assert runtime._bundled_dir() is None


# ----- Loading ------------------------------------------------------------


def test_load_reports_a_reason_instead_of_raising(monkeypatch, windows):
    monkeypatch.setattr(runtime, "find_runtime", lambda: None)

    module, error = runtime.load_vlc()

    assert module is None
    assert runtime.DIR_ENV_VAR in error
    assert runtime.is_available() is False


def test_load_prepares_the_environment_before_importing(monkeypatch, tmp_path, windows):
    directory = make_vlc_dir(tmp_path)
    found = runtime.Runtime(
        directory, directory / "libvlc.dll", directory / "plugins", "test"
    )
    monkeypatch.setattr(runtime, "find_runtime", lambda: found)
    added = []
    monkeypatch.setattr(runtime.os, "add_dll_directory", added.append, raising=False)

    runtime.load_vlc()

    # These two are what python-vlc's own loader reads. Without them it falls
    # back to `CDLL(".\\libvlc.dll")`, which resolves against the working
    # directory and finds nothing — the bug this test exists to prevent.
    assert runtime.os.environ["PYTHON_VLC_LIB_PATH"] == str(directory / "libvlc.dll")
    assert runtime.os.environ["PYTHON_VLC_MODULE_PATH"] == str(directory / "plugins")
    assert runtime.os.environ["VLC_PLUGIN_PATH"] == str(directory / "plugins")
    assert added == [str(directory)]


def test_find_runtime_reports_the_library_path(monkeypatch, tmp_path, windows):
    directory = make_vlc_dir(tmp_path)
    monkeypatch.setenv(runtime.DIR_ENV_VAR, str(directory))
    monkeypatch.setattr(runtime, "_registry_dirs", list)

    assert runtime.find_runtime().library == directory / "libvlc.dll"


def test_load_survives_python_vlc_calling_sys_exit(monkeypatch, tmp_path, windows):
    # python-vlc calls sys.exit(1) rather than raising when the library it was
    # handed will not load. SystemExit is a BaseException, so an `except
    # Exception` guard would let it through and kill the app.
    directory = make_vlc_dir(tmp_path)
    monkeypatch.setattr(
        runtime,
        "find_runtime",
        lambda: runtime.Runtime(
            directory, directory / "libvlc.dll", directory / "plugins", "test"
        ),
    )
    monkeypatch.setattr(runtime.os, "add_dll_directory", lambda path: None, raising=False)

    import builtins

    real_import = builtins.__import__

    def bail(name, *args, **kwargs):
        if name == "vlc":
            raise SystemExit(1)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", bail)

    module, error = runtime.load_vlc()

    assert module is None
    assert "refused to load" in error


def test_load_turns_an_import_failure_into_a_message(monkeypatch, tmp_path, windows):
    directory = make_vlc_dir(tmp_path)
    monkeypatch.setattr(
        runtime,
        "find_runtime",
        lambda: runtime.Runtime(
            directory, directory / "libvlc.dll", directory / "plugins", "test"
        ),
    )
    monkeypatch.setattr(runtime.os, "add_dll_directory", lambda path: None, raising=False)

    import builtins

    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "vlc":
            raise OSError("libvlc.dll is not a valid Win32 application")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse)

    module, error = runtime.load_vlc()

    assert module is None
    assert "Could not load VLC" in error


def test_load_is_cached(monkeypatch, windows):
    calls = {"n": 0}

    def counted():
        calls["n"] += 1
        return None

    monkeypatch.setattr(runtime, "find_runtime", counted)

    runtime.load_vlc()
    runtime.load_vlc()
    assert calls["n"] == 1

    runtime.load_vlc(force=True)
    assert calls["n"] == 2


def test_describe_explains_an_unavailable_player(monkeypatch, windows):
    monkeypatch.setattr(runtime, "find_runtime", lambda: None)

    info = runtime.describe()

    assert info["available"] is False
    assert info["reason"]
    assert info["version"] == ""
    assert info["directory"] == ""


def test_describe_reports_a_working_player(monkeypatch, tmp_path, windows):
    directory = make_vlc_dir(tmp_path)
    found = runtime.Runtime(
        directory, directory / "libvlc.dll", directory / "plugins", "test"
    )
    monkeypatch.setattr(runtime, "find_runtime", lambda: found)

    class FakeVlc:
        @staticmethod
        def libvlc_get_version():
            return b"3.0.20 Vetinari"

    monkeypatch.setattr(runtime, "load_vlc", lambda force=False: (FakeVlc, ""))

    info = runtime.describe()

    assert info["available"] is True
    assert info["version"] == "3.0.20 Vetinari"
    assert info["directory"] == str(directory)
    assert info["source"] == "test"


# ----- Backend ------------------------------------------------------------


def test_create_player_returns_none_without_a_runtime(monkeypatch):
    monkeypatch.setattr(backend, "load_vlc", lambda: (None, "no VLC here"))

    assert backend.create_player() is None


def test_constructing_a_player_without_a_runtime_raises(monkeypatch):
    monkeypatch.setattr(backend, "load_vlc", lambda: (None, "no VLC here"))

    with pytest.raises(backend.PlayerUnavailable, match="no VLC here"):
        backend.VlcPlayer()


@pytest.mark.parametrize(
    "value, expected",
    [(-10, 0), (0, 0), (55, 55), (100, 100), (250, 100), ("nope", 0), (None, 0)],
)
def test_clamp_volume(value, expected):
    assert backend.clamp_volume(value) == expected


# ----- Window helpers -----------------------------------------------------


@pytest.mark.parametrize(
    "milliseconds, expected",
    [
        (-1, "--:--"),
        (None, "--:--"),
        (0, "0:00"),
        (9_000, "0:09"),
        (65_000, "1:05"),
        (599_000, "9:59"),
        (3_600_000, "1:00:00"),
        (3_725_000, "1:02:05"),
    ],
)
def test_format_time(milliseconds, expected):
    assert format_time(milliseconds) == expected


# ----- Growing-file source ------------------------------------------------
#
# VLC's ordinary file access reports end-of-stream at the last byte on disk,
# which ends a still-downloading torrent early: measured against a real libvlc,
# a file opened at 25% played exactly 25% and stopped. These cover the read
# callback that waits instead.


class Buffer:
    """Somewhere for the read callback to memmove into."""

    def __init__(self, size=4096):
        self.raw = ctypes.create_string_buffer(size)

    def value(self, length):
        return self.raw.raw[:length]


def growing_file(tmp_path, present: bytes, total: int, **kwargs):
    path = tmp_path / "growing.bin"
    path.write_bytes(present)
    src = source.GrowingFile(str(path), total, **kwargs)
    src.open(None, None, None)
    return src, path


def test_source_reads_what_is_already_there(tmp_path):
    src, _ = growing_file(tmp_path, b"abcdef", 6)
    buf = Buffer()

    n = src.read(None, buf.raw, 6)

    assert n == 6
    assert buf.value(n) == b"abcdef"
    assert src.position == 6


def test_source_reports_end_of_stream_at_the_real_end(tmp_path):
    src, _ = growing_file(tmp_path, b"abcdef", 6)
    buf = Buffer()
    src.read(None, buf.raw, 6)

    # Everything the torrent will ever contain has been read.
    assert src.read(None, buf.raw, 6) == 0


def test_source_waits_for_bytes_that_have_not_arrived(tmp_path):
    # Only 3 of 6 bytes present: the read must block, not report EOF.
    src, path = growing_file(tmp_path, b"abc", 6, poll_seconds=0.02)
    buf = Buffer()
    assert src.read(None, buf.raw, 3) == 3

    def finish():
        time.sleep(0.15)
        with open(path, "ab") as fh:
            fh.write(b"def")

    thread = threading.Thread(target=finish)
    thread.start()
    n = src.read(None, buf.raw, 3)   # blocks until finish() appends
    thread.join()

    assert n == 3
    assert buf.value(n) == b"def"
    assert src.waits > 0, "the read returned without ever waiting"


def test_source_gives_up_after_a_stall(tmp_path):
    # A torrent can simply stop making progress; waiting forever is a hang.
    src, _ = growing_file(tmp_path, b"abc", 6, poll_seconds=0.01, stall_timeout=0.05)
    buf = Buffer()
    src.read(None, buf.raw, 3)

    assert src.read(None, buf.raw, 3) == 0


def test_source_cancel_unblocks_a_waiting_read(tmp_path):
    # libvlc's contract: the callback must return an error when playback stops,
    # or libvlc_media_player_stop never returns and the UI thread wedges.
    src, _ = growing_file(tmp_path, b"abc", 6, poll_seconds=0.01, stall_timeout=30)
    buf = Buffer()
    src.read(None, buf.raw, 3)

    threading.Timer(0.1, src.cancel).start()
    started = time.time()
    n = src.read(None, buf.raw, 3)

    assert n == -1
    assert time.time() - started < 5, "cancel did not unblock the read"


def test_source_read_is_capped_by_what_is_available(tmp_path):
    src, _ = growing_file(tmp_path, b"abc", 100)
    buf = Buffer()

    # Asked for 50, only 3 exist: return the 3 rather than waiting for 50.
    assert src.read(None, buf.raw, 50) == 3


def test_source_seek_moves_the_position(tmp_path):
    src, _ = growing_file(tmp_path, b"abcdef", 6)
    buf = Buffer()

    assert src.seek(None, 3) == 0
    assert src.read(None, buf.raw, 3) == 3
    assert buf.value(3) == b"def"


def test_source_seek_past_the_downloaded_region_then_waits(tmp_path):
    src, path = growing_file(tmp_path, b"abc", 9, poll_seconds=0.01, stall_timeout=0.05)
    buf = Buffer()

    src.seek(None, 6)
    assert src.read(None, buf.raw, 3) == 0  # nothing there yet, and it stalls

    path.write_bytes(b"abcdefghi")
    src.seek(None, 6)
    assert src.read(None, buf.raw, 3) == 3
    assert buf.value(3) == b"ghi"


def test_source_close_is_safe_twice(tmp_path):
    src, _ = growing_file(tmp_path, b"abc", 3)

    src.close(None)
    src.close(None)  # must not raise


@pytest.mark.parametrize(
    "present, total, expected",
    [(b"abc", 10, True), (b"abcdefghij", 10, False), (b"abc", 0, False), (b"abc", -1, False)],
)
def test_is_incomplete(tmp_path, present, total, expected):
    path = tmp_path / "f.bin"
    path.write_bytes(present)

    assert source.is_incomplete(str(path), total) is expected


def test_is_incomplete_is_false_for_a_missing_file(tmp_path):
    assert source.is_incomplete(str(tmp_path / "nope.bin"), 100) is False


def test_a_portable_copy_in_the_data_dir_is_found(monkeypatch, tmp_path, windows):
    # Installing VLC properly needs administrator rights; dropping a portable
    # copy into Yoink's own data folder does not.
    portable = make_vlc_dir(tmp_path, "vlc")
    monkeypatch.delenv(runtime.DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(runtime, "_data_dir", lambda: portable)

    found = runtime.find_runtime()

    assert found.directory == portable
    assert found.source == "data dir"


def test_a_bundled_copy_beats_the_data_dir(monkeypatch, tmp_path, windows):
    bundled = make_vlc_dir(tmp_path, "bundled")
    portable = make_vlc_dir(tmp_path, "portable")
    monkeypatch.delenv(runtime.DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(runtime, "_bundled_dir", lambda: bundled)
    monkeypatch.setattr(runtime, "_data_dir", lambda: portable)

    assert runtime.find_runtime().directory == bundled
