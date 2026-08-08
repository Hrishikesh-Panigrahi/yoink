"""Recover torrents deleted from Yoink's database.

SQLite does not zero deleted rows - they sit in the file's free pages until
something reuses them. So a torrent removed by an accidental click is usually
still readable straight out of the database file.

    python recover_torrents.py [--db PATH] [--out FILE]

Prints every magnet link and info hash it can find, live or deleted. Run it
sooner rather than later: the free pages are reused as the app writes.

This only reads the file. Re-adding anything is left to a human, because
adding a torrent starts announcing to trackers.
"""

from __future__ import annotations

import argparse
import os
import re

MAGNET = re.compile(r"magnet:\?xt=urn:btih:[^\x00-\x1f]+")
INFO_HASH = re.compile(r"\b[0-9a-fA-F]{40}\b")


def default_db() -> str:
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(root, "Yoink", "yoink.db")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=default_db())
    parser.add_argument("--out", help="also write the magnets to this file")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"no database at {args.db}")

    raw = open(args.db, "rb").read().decode("latin-1")

    # Longest wins: a row can appear truncated in one page and whole in another.
    magnets = {}
    for match in MAGNET.finditer(raw):
        text = match.group(0)
        key = re.search(r"btih:([0-9a-fA-F]{40})", text)
        if not key:
            continue
        digest = key.group(1).upper()
        if len(text) > len(magnets.get(digest, "")):
            magnets[digest] = text

    print(f"database: {args.db}")
    print(f"magnets recovered: {len(magnets)}\n")
    for digest, text in magnets.items():
        name = re.search(r"&dn=([^&]+)", text)
        print(f"  {digest}")
        if name:
            print(f"    name:     {name.group(1)[:90]}")
        print(f"    trackers: {text.count('&tr=')}")
        print(f"    magnet:   {text[:100]}...")
        print()

    loose = {h.upper() for h in INFO_HASH.findall(raw)} - set(magnets)
    if loose:
        print("info hashes with no magnet attached:")
        for digest in sorted(loose):
            print(f"  {digest}")

    if args.out and magnets:
        with open(args.out, "w", encoding="utf-8") as handle:
            for text in magnets.values():
                handle.write(text + "\n")
        print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
