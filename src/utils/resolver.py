"""Resolve hostnames over DNS-over-HTTPS instead of the system resolver.

Some networks answer DNS for torrent sites with a sinkhole address, so every
connection times out. DoH returns the real addresses.

This patches `socket.getaddrinfo` instead of rewriting URLs to IP addresses.
Rewriting URLs breaks SNI, the Host header and certificate checks. Patching the
lookup keeps all three working, for `requests`, `urllib` and `aiohttp` alike.

Nothing is patched at import time. `apply_from_settings()` turns it on or off from
the `dns_over_https_enabled` setting, which defaults to on.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Dict, List, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from utils.logger import setup_logger

logger = setup_logger("utils.resolver")

#: Queried in order until one answers. Both speak the same JSON API.
DOH_ENDPOINTS: Tuple[str, ...] = (
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
)

#: Looking these up over DoH would recurse, so they use the system resolver.
_RESOLVER_HOSTS = frozenset({"cloudflare-dns.com", "dns.google"})

CACHE_TTL_SECONDS = 300.0
LOOKUP_TIMEOUT_SECONDS = 5.0

_cache: Dict[str, Tuple[float, List[str]]] = {}
_lock = threading.Lock()
_system_getaddrinfo = socket.getaddrinfo
_installed = False


def lookup(host: str) -> List[str]:
    """Return the A records for `host` from DoH, or an empty list.

    Empty answers are cached too, so a dead site isn't looked up on every request.
    """
    host = (host or "").strip().rstrip(".")
    if not host or host in _RESOLVER_HOSTS:
        return []

    now = time.monotonic()
    with _lock:
        hit = _cache.get(host)
        if hit and now - hit[0] < CACHE_TTL_SECONDS:
            return list(hit[1])

    addresses = _query(host)
    with _lock:
        _cache[host] = (now, addresses)
    return list(addresses)


def _query(host: str) -> List[str]:
    for endpoint in DOH_ENDPOINTS:
        url = f"{endpoint}?{urlencode({'name': host, 'type': 'A'})}"
        request = Request(url, headers={"Accept": "application/dns-json"})
        try:
            with urlopen(request, timeout=LOOKUP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.debug(f"DoH lookup of {host} via {endpoint} failed: {exc}")
            continue
        answers = [
            entry.get("data")
            for entry in payload.get("Answer", [])
            if entry.get("type") == 1 and entry.get("data")
        ]
        if answers:
            logger.info(f"DoH resolved {host} -> {', '.join(answers)}")
            return answers
        # A valid response with no A record means the name really has none;
        # asking the other resolver will not change that.
        logger.debug(f"DoH: {host} has no A record")
        return []
    return []


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Use DoH for IPv4 name lookups and fall back to the system resolver otherwise."""
    try:
        name = host.decode() if isinstance(host, bytes) else host
        if name and family in (0, socket.AF_INET) and not _looks_like_an_address(name):
            addresses = lookup(name)
            if addresses:
                sock_type = type or socket.SOCK_STREAM
                return [
                    (socket.AF_INET, sock_type, proto or 0, "", (address, port))
                    for address in addresses
                ]
    except Exception as exc:
        logger.debug(f"DoH getaddrinfo path failed for {host}: {exc}")
    return _system_getaddrinfo(host, port, family, type, proto, flags)


def _looks_like_an_address(name: str) -> bool:
    """Literal addresses and localhost must never go to a public resolver."""
    if name in ("localhost", "localhost.localdomain"):
        return True
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            socket.inet_pton(family, name)
            return True
        except (OSError, ValueError):
            continue
    return False


def install() -> bool:
    global _installed
    if _installed:
        return True
    socket.getaddrinfo = _patched_getaddrinfo
    _installed = True
    logger.info("DNS-over-HTTPS resolution enabled")
    return True


def uninstall() -> None:
    global _installed
    if not _installed:
        return
    socket.getaddrinfo = _system_getaddrinfo
    _installed = False
    logger.info("DNS-over-HTTPS resolution disabled")


def is_installed() -> bool:
    return _installed


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def apply_from_settings() -> bool:
    import db

    enabled = (db.get_setting("dns_over_https_enabled") or "1") == "1"
    if enabled:
        install()
    else:
        uninstall()
    return enabled
