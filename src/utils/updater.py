"""GitHub Releases auto-update checker.

Hits the public Releases API for our repo and returns the latest tag +
download URL when it differs from the running version. The UI shows a
"new version available" banner; we don't push downloads silently.
"""

from __future__ import annotations

from typing import Optional

import requests

from utils.logger import setup_logger
from version import __release_api__, __version__

logger = setup_logger("utils.updater")


def check_for_update(timeout: float = 6.0) -> Optional[dict]:
    """Return release info if a newer tag is published, otherwise ``None``.

    Result shape:
        {
            "current": "2.0.0",
            "latest": "2.1.0",
            "url": "https://github.com/.../releases/tag/v2.1.0",
            "downloadUrl": "https://...Yoink-Setup-2.1.0.exe" | None,
            "checksumUrl": "https://...SHA256SUMS.txt" | None,
            "notes": str,
        }
    """
    try:
        response = requests.get(
            __release_api__,
            headers={"Accept": "application/vnd.github+json"},
            timeout=timeout,
        )
        if response.status_code == 404:
            logger.info("No releases published yet")
            return None
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning(f"Update check failed: {exc}")
        return None

    latest_tag = (data.get("tag_name") or "").lstrip("v").strip()
    if not latest_tag:
        return None
    if _normalize_version(latest_tag) <= _normalize_version(__version__):
        return None

    download_url: Optional[str] = None
    checksum_url: Optional[str] = None
    assets = data.get("assets") or []
    for asset in assets:
        name = (asset.get("name") or "").lower()
        if name == "sha256sums.txt":
            checksum_url = asset.get("browser_download_url")
            break

    for asset in assets:
        name = (asset.get("name") or "").lower()
        if name.endswith(".exe") and "setup" in name:
            download_url = asset.get("browser_download_url")
            break
    if download_url is None:
        for asset in assets:
            name = (asset.get("name") or "").lower()
            if name.endswith(".exe"):
                download_url = asset.get("browser_download_url")
                break

    return {
        "current": __version__,
        "latest": latest_tag,
        "url": data.get("html_url") or "",
        "downloadUrl": download_url,
        "checksumUrl": checksum_url,
        "notes": data.get("body") or "",
    }


def _normalize_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in value.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            parts.append(int(digits))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)
