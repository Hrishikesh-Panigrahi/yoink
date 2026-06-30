from __future__ import annotations

from pathlib import Path

from utils import paths


def test_default_db_path_uses_local_app_data(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    db_path = Path(paths.default_db_path())

    assert db_path == tmp_path / "Yoink" / "yoink.db"


def test_logs_dir_is_created(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    log_dir = Path(paths.logs_dir())

    assert log_dir == tmp_path / "Yoink" / "logs"
    assert log_dir.is_dir()
