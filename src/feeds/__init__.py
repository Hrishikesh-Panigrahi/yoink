"""RSS feed subscription helpers.

Backed by the existing settings table to avoid schema migrations:
- ``rss.feeds`` stores a JSON list of feed configs.
- ``rss.seen.<feed_id>`` stores a comma-separated list of GUIDs we've already added.
"""

from __future__ import annotations

import json
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List
from urllib.request import Request, urlopen

import db
from utils.logger import setup_logger

logger = setup_logger("feeds")

SETTINGS_KEY = "rss.feeds"
MAX_SEEN_PER_FEED = 200


@dataclass
class FeedConfig:
    id: str
    url: str
    name: str = ""
    filter_regex: str = ""
    min_seeders: int = 0
    enabled: bool = True
    created_at: float = field(default_factory=time.time)


def load_feeds() -> List[FeedConfig]:
    raw = db.get_setting(SETTINGS_KEY) or "[]"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out: List[FeedConfig] = []
    for item in payload:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        out.append(
            FeedConfig(
                id=item.get("id") or uuid.uuid4().hex,
                url=item["url"],
                name=item.get("name", ""),
                filter_regex=item.get("filter_regex", ""),
                min_seeders=int(item.get("min_seeders", 0) or 0),
                enabled=bool(item.get("enabled", True)),
                created_at=float(item.get("created_at", time.time())),
            )
        )
    return out


def save_feeds(feeds: List[FeedConfig]) -> None:
    payload = [
        {
            "id": f.id,
            "url": f.url,
            "name": f.name,
            "filter_regex": f.filter_regex,
            "min_seeders": f.min_seeders,
            "enabled": f.enabled,
            "created_at": f.created_at,
        }
        for f in feeds
    ]
    db.set_setting(SETTINGS_KEY, json.dumps(payload))


def add_feed(url: str, name: str = "", filter_regex: str = "", min_seeders: int = 0) -> FeedConfig:
    feeds = load_feeds()
    cfg = FeedConfig(
        id=uuid.uuid4().hex, url=url, name=name, filter_regex=filter_regex, min_seeders=min_seeders
    )
    feeds.append(cfg)
    save_feeds(feeds)
    return cfg


def remove_feed(feed_id: str) -> bool:
    feeds = load_feeds()
    keep = [f for f in feeds if f.id != feed_id]
    if len(keep) == len(feeds):
        return False
    save_feeds(keep)
    return True


def _seen_key(feed_id: str) -> str:
    return f"rss.seen.{feed_id}"


def get_seen(feed_id: str) -> set:
    raw = db.get_setting(_seen_key(feed_id)) or ""
    return {part for part in raw.split(",") if part}


def mark_seen(feed_id: str, guids: List[str]) -> None:
    seen = get_seen(feed_id) | set(guids)
    if len(seen) > MAX_SEEN_PER_FEED:
        seen = set(list(seen)[-MAX_SEEN_PER_FEED:])
    db.set_setting(_seen_key(feed_id), ",".join(sorted(seen)))


def fetch_feed_items(url: str, timeout: float = 10.0) -> List[dict]:
    """Return a list of ``{title, magnet, guid, seeders}`` items from an RSS feed."""
    try:
        req = Request(url, headers={"User-Agent": "Yoink-RSS/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception as exc:
        logger.warning(f"Could not fetch RSS feed {url}: {exc}")
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        logger.warning(f"Malformed RSS feed at {url}: {exc}")
        return []
    items: List[dict] = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        magnet = link if link.startswith("magnet:") else ""
        enclosure = item.find("enclosure")
        if not magnet and enclosure is not None:
            enc_url = (enclosure.get("url") or "").strip()
            if enc_url.startswith("magnet:"):
                magnet = enc_url
        if not magnet:
            # Some feeds put the magnet in <torrent xmlns="..."><magnetURI>...
            for child in item.iter():
                if child.tag.endswith("magnetURI") and (child.text or "").startswith("magnet:"):
                    magnet = child.text.strip()
                    break
        if not magnet:
            continue
        guid = (item.findtext("guid") or magnet).strip()
        title = (item.findtext("title") or "").strip()
        seeders = 0
        for child in item.iter():
            if child.tag.endswith("seeders"):
                try:
                    seeders = int((child.text or "0").strip())
                except (ValueError, TypeError):
                    seeders = 0
                break
        items.append({"title": title, "magnet": magnet, "guid": guid, "seeders": seeders})
    return items
