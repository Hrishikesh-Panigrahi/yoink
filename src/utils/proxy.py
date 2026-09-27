"""Send search traffic through the proxy saved in Settings > Advanced.

This sets the standard proxy environment variables, which `requests` reads by
default and the vendored scrapers read through `aiohttp`'s `trust_env=True`.
Torrent traffic itself (libtorrent) and the DNS-over-HTTPS lookups in
utils.resolver don't go through it.
"""

from __future__ import annotations

import os
from typing import Dict, Optional
from urllib.parse import urlparse

SUPPORTED_SCHEMES = ("http", "https")
_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy")
_NO_PROXY = "localhost,127.0.0.1,::1"

# Whatever the environment held before Yoink set anything, so clearing the
# proxy puts back a system-wide proxy instead of deleting it.
_original: Optional[Dict[str, Optional[str]]] = None
_active = ""
_user_agent = ""


def normalize(proxy_url: str) -> str:
    """Trim it, and treat a bare `host:port` as an http:// proxy."""
    url = (proxy_url or "").strip()
    if url and "://" not in url:
        url = "http://" + url
    return url


def problem_with(proxy_url: str) -> Optional[str]:
    """Why this proxy URL can't be used, or None if it's fine (or empty)."""
    url = normalize(proxy_url)
    if not url:
        return None
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme.startswith("socks"):
        return "SOCKS proxies aren't supported yet. Use an http:// or https:// proxy."
    if scheme not in SUPPORTED_SCHEMES:
        return f"Unknown proxy type '{scheme}'. Use an http:// or https:// proxy."
    try:
        port = parsed.port
    except ValueError:
        port = None
    if not parsed.hostname or not port:
        return "A proxy needs a host and a port, like http://203.0.113.7:8080."
    return None


def apply(proxy_url: str, user_agent: str = "") -> Optional[str]:
    """Route search traffic through `proxy_url`, or stop if it's empty.

    Returns an error message and changes nothing when the URL can't be used.
    """
    global _original, _active, _user_agent
    url = normalize(proxy_url)
    error = problem_with(url)
    if error:
        return error
    if _original is None:
        _original = {key: os.environ.get(key) for key in _ENV_KEYS}
    for key in _ENV_KEYS:
        if url:
            value = _NO_PROXY if key.lower() == "no_proxy" else url
        else:
            value = _original.get(key)
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
    _active = url
    _user_agent = (user_agent or "").strip()
    return None


def active() -> str:
    return _active


def user_agent(default: str) -> str:
    return _user_agent or default


def apply_from_settings() -> Optional[str]:
    import db

    return apply(db.get_setting("proxy_url") or "", db.get_setting("user_agent") or "")
