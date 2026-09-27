"""Status checks for the Sources panel: each provider runs a small test search
and is graded ok, slow or down by how long it took.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from providers import torrent_api_py
from providers.pirate_bay import search_pirate_bay
from search.enums import Category
from utils.logger import setup_logger

logger = setup_logger("providers.health")

# Latency limits in seconds for the "ok" and "slow" grades.
_OK_LATENCY = 4.0
_SLOW_LATENCY = 12.0
_PROBE_QUERY = "matrix"
_CACHE_TTL_SECONDS = 300.0
_cache: tuple[float, Dict[str, dict]] | None = None


def ping_all(timeout_seconds: float = 12.0, *, force: bool = False) -> Dict[str, dict]:
    """Probe every provider in parallel.

    The keys match those from `providers.all_provider_choices()`, which the UI relies on.
    """
    global _cache
    now = time.monotonic()
    if not force and _cache is not None:
        cached_at, statuses = _cache
        if now - cached_at <= _CACHE_TTL_SECONDS:
            return statuses

    probes = _probe_specs()
    with ThreadPoolExecutor(max_workers=min(10, len(probes) or 1)) as pool:
        futures = {
            pool.submit(_probe, name, fn, timeout_seconds): key
            for key, (name, fn) in probes.items()
        }
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
        "piratebay_stable": (
            "The Pirate Bay",
            lambda: search_pirate_bay(_PROBE_QUERY, 1, 1),
        ),
    }
    for key in torrent_api_py.available_sites():
        specs[f"vendor:{key}"] = (
            key,
            (lambda k=key: torrent_api_py.search_multi_site(
                _PROBE_QUERY, 1, sites=[k], category=Category.ANY,
                limit_per_site=1, timeout_seconds=8.0,
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
        # An empty list still means the site answered. Only None counts as down.
        if result is None:
            status = "down"
        return {"status": status, "latencyMs": int(elapsed * 1000), "error": ""}
    except Exception as exc:
        elapsed = time.monotonic() - started
        return {"status": "down", "latencyMs": int(elapsed * 1000), "error": str(exc)}
