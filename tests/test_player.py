"""Tests for `src/player/`.

No libvlc is installed on a CI runner, and that is the interesting case: the
whole point of `player.runtime` is that a missing runtime produces a reason
rather than an exception at import time. Discovery is driven against temporary
directories shaped like a real VLC install, so it is tested without one.

Actual video decoding is not covered here — that needs a real library, a real
window and a real file.
"""

from __future__ import annotations

import pytest

from player import backend, runtime
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
    found = runtime.Runtime(directory, directory / "plugins", "test")
    monkeypatch.setattr(runtime, "find_runtime", lambda: found)
    added = []
    monkeypatch.setattr(runtime.os, "add_dll_directory", added.append, raising=False)

    runtime.load_vlc()

    assert runtime.os.environ["VLC_PLUGIN_PATH"] == str(directory / "plugins")
    assert added == [str(directory)]


def test_load_turns_an_import_failure_into_a_message(monkeypatch, tmp_path, windows):
    directory = make_vlc_dir(tmp_path)
    monkeypatch.setattr(
        runtime, "find_runtime", lambda: runtime.Runtime(directory, directory, "test")
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
    found = runtime.Runtime(directory, directory / "plugins", "test")
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
