"""Find a working free proxy from public lists on GitHub.

Only a few percent of listed proxies answer at all, so many are tried at once
and the search stops as soon as a handful work. Of those, the fastest one that
also reaches a site Indian providers block (Nyaa) wins, since getting past the
block is usually the point.
"""

from __future__ import annotations

import random
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed, wait
from typing import Callable, Dict, List, Optional

import requests

from utils.logger import setup_logger

logger = setup_logger("free_proxies")

LISTS = (
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
)
WORKS_URL = "https://apibay.org/q.php?q=ubuntu&cat=0"
UNBLOCK_URL = "https://nyaa.si/?q=ubuntu"
UNBLOCK_MARKER = "torrent-list"

MAX_CANDIDATES = 500
MAX_WORKING = 8
DEADLINE_SECONDS = 45.0
PARALLEL_CHECKS = 64
CHECK_TIMEOUT = 8.0
UNBLOCK_TIMEOUT = 12.0

_ADDRESS = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})\b")
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

Progress = Callable[[int, int, int], None]


def _session() -> requests.Session:
    # Ignore any proxy that's already set: it may be the dead one being replaced.
    session = requests.Session()
    session.trust_env = False
    session.headers.update(_HEADERS)
    return session


def _through(proxy: str, url: str, timeout: float) -> requests.Response:
    address = f"http://{proxy}"
    return _session().get(url, proxies={"http": address, "https": address}, timeout=timeout)


def _fetch_list(url: str) -> List[str]:
    try:
        # A short connect timeout: now and then one of GitHub's addresses doesn't answer,
        # and the next one should be tried after a few seconds, not after the full wait.
        return _ADDRESS.findall(_session().get(url, timeout=(4, 15)).text)
    except requests.RequestException as exc:
        logger.warning(f"Could not fetch proxy list {url}: {exc}")
        return []


def fetch_candidates() -> List[str]:
    """Every `ip:port` in the lists, deduplicated and shuffled."""
    with ThreadPoolExecutor(len(LISTS)) as pool:
        found = {address for addresses in pool.map(_fetch_list, LISTS) for address in addresses}
    candidates = sorted(found)
    random.shuffle(candidates)
    return candidates


def check(proxy: str, timeout: float = CHECK_TIMEOUT) -> Optional[float]:
    """Seconds The Pirate Bay's API took to answer through `proxy`, or None."""
    started = time.monotonic()
    try:
        data = _through(proxy, WORKS_URL, timeout).json()
    except Exception:
        return None
    if isinstance(data, list) and data and isinstance(data[0], dict) and "info_hash" in data[0]:
        return time.monotonic() - started
    return None


def reaches_blocked_site(proxy: str, timeout: float = UNBLOCK_TIMEOUT) -> bool:
    try:
        response = _through(proxy, UNBLOCK_URL, timeout)
    except Exception:
        return False
    return response.status_code == 200 and UNBLOCK_MARKER in response.text


def find(
    on_progress: Optional[Progress] = None,
    should_stop: Callable[[], bool] = lambda: False,
    candidates: Optional[List[str]] = None,
) -> Optional[dict]:
    """Return {"proxy", "latency", "reachesBlocked", "tested"} for the best proxy, or None.

    Each proxy that works is checked against the blocked site straight away, and
    the search stops at the first one that gets through. Otherwise it keeps going
    until MAX_WORKING work, the candidates run out or the deadline passes, then
    settles for the fastest working one.
    """
    if candidates is None:
        candidates = fetch_candidates()
    candidates = candidates[:MAX_CANDIDATES]
    deadline = time.monotonic() + DEADLINE_SECONDS
    working: List[tuple] = []
    unblock_checks: Dict[str, Future] = {}
    tested = 0
    checks = ThreadPoolExecutor(PARALLEL_CHECKS)
    unblocks = ThreadPoolExecutor(4)
    try:
        futures = {checks.submit(check, proxy): proxy for proxy in candidates}
        for future in as_completed(futures):
            tested += 1
            latency = future.result()
            if latency is not None:
                proxy = futures[future]
                working.append((latency, proxy))
                unblock_checks[proxy] = unblocks.submit(reaches_blocked_site, proxy)
            if on_progress:
                on_progress(tested, len(candidates), len(working))
            if (should_stop() or time.monotonic() > deadline or len(working) >= MAX_WORKING
                    or _got_through(unblock_checks)):
                break
        if unblock_checks and not _got_through(unblock_checks) and not should_stop():
            wait(unblock_checks.values(), timeout=UNBLOCK_TIMEOUT)
    finally:
        # Checks still running finish on their own timeouts; nobody waits for them.
        checks.shutdown(wait=False, cancel_futures=True)
        unblocks.shutdown(wait=False, cancel_futures=True)

    if should_stop() or not working:
        return None
    through = {proxy for proxy, check_ in unblock_checks.items() if _passed(check_)}
    latency, proxy = min(working, key=lambda item: (item[1] not in through, item[0]))
    return {
        "proxy": f"http://{proxy}",
        "latency": round(latency, 1),
        "reachesBlocked": proxy in through,
        "tested": tested,
    }


def _passed(check_: Future) -> bool:
    return check_.done() and not check_.cancelled() and bool(check_.result())


def _got_through(unblock_checks: Dict[str, Future]) -> bool:
    return any(_passed(check_) for check_ in unblock_checks.values())
