"""Lightweight health pings for every available provider.

Each ping issues a tiny test search and times how long it took. We grade
the result on three bands so the Sources panel can show a quick traffic
light per source.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from providers import torrent_api_py
from providers.pirate_bay import search_pirate_bay
from providers.yts import search_yts
from utils.logger import setup_logger

logger = setup_logger("providers.health")

# Grades: "ok" <= 4s, "slow" <= 12s, "down" otherwise / on exception.
_OK_LATENCY = 4.0
_SLOW_LATENCY = 12.0
_PROBE_QUERY = "matrix"
_CACHE_TTL_SECONDS = 300.0
_cache: tuple[float, Dict[str, dict]] | None = None


def ping_all(timeout_seconds: float = 12.0, *, force: bool = False) -> Dict[str, dict]:
    """Concurrently probe every provider and return a status map.

    Keys mirror those exposed by ``providers.all_provider_choices`` so the
    web UI can directly index into the response.
    """
    global _cache
    now = time.monotonic()
    if not force and _cache is not None:
        cached_at, statuses = _cache
        if now - cached_at <= _CACHE_TTL_SECONDS:
            return statuses

    probes = _probe_specs()
    with ThreadPoolExecutor(max_workers=min(10, len(probes) or 1)) as pool:
        futures = {pool.submit(_probe, name, fn, timeout_seconds): key for key, (name, fn) in probes.items()}
        out: Dict[str, dict] = {}
        for future, key in futures.items():
            try:
                out[key] = future.result()
            except Exception as exc:
                logger.warning(f"health probe failed for {key}: {exc}")
                out[key] = {"status": "down", "latencyMs": 0, "error": str(exc)}
    _cache = (time.monotonic(), out)
    return out


def _probe_specs() -> Dict[str, tuple[str, callable]]:
    specs: Dict[str, tuple[str, callable]] = {
        "yts": ("YTS", lambda: search_yts(_PROBE_QUERY, 1)),
        "piratebay_stable": (
            "The Pirate Bay",
            lambda: search_pirate_bay(_PROBE_QUERY, 1, 1),
        ),
    }
    for key in torrent_api_py.available_sites():
        specs[f"vendor:{key}"] = (
            key,
            (lambda k=key: torrent_api_py.search_multi_site(
                _PROBE_QUERY, 1, sites=[k], limit_per_site=1, timeout_seconds=8.0
            )),
        )
    return specs


def _probe(name: str, fn, timeout_seconds: float) -> dict:
    started = time.monotonic()
    try:
        result = fn()
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            return {"status": "down", "latencyMs": int(elapsed * 1000), "error": "timeout"}
        status = "ok" if elapsed <= _OK_LATENCY else "slow" if elapsed <= _SLOW_LATENCY else "down"
        # An empty result for a generic probe still means the site answered.
        if result is None:
            status = "down"
        return {"status": status, "latencyMs": int(elapsed * 1000), "error": ""}
    except Exception as exc:
        elapsed = time.monotonic() - started
        return {"status": "down", "latencyMs": int(elapsed * 1000), "error": str(exc)}
