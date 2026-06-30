from __future__ import annotations

import responses

from utils import updater
from version import __release_api__


@responses.activate
def test_check_for_update_prefers_installer_and_returns_checksum() -> None:
    responses.add(
        responses.GET,
        __release_api__,
        json={
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/Hrishikesh-Panigrahi/yoink/releases/tag/v9.9.9",
            "body": "Release notes",
            "assets": [
                {"name": "Yoink.exe", "browser_download_url": "https://example.com/Yoink.exe"},
                {"name": "Yoink-Setup-9.9.9.exe", "browser_download_url": "https://example.com/setup.exe"},
                {"name": "SHA256SUMS.txt", "browser_download_url": "https://example.com/SHA256SUMS.txt"},
            ],
        },
        status=200,
    )

    result = updater.check_for_update()

    assert result is not None
    assert result["latest"] == "9.9.9"
    assert result["downloadUrl"] == "https://example.com/setup.exe"
    assert result["checksumUrl"] == "https://example.com/SHA256SUMS.txt"


@responses.activate
def test_check_for_update_returns_none_for_current_version() -> None:
    responses.add(
        responses.GET,
        __release_api__,
        json={"tag_name": "v2.0.0", "assets": []},
        status=200,
    )

    assert updater.check_for_update() is None
