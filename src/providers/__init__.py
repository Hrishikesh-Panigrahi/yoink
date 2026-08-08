"""Per-source torrent search adapters.

Import the concrete adapter modules directly
(`from providers.yts import search_yts`) — this package intentionally
avoids re-exports to prevent circular imports with `search/`.
"""

from providers.torrent_api_py import available_sites, site_configs

#: Stable APIs that always show as toggleable in Settings -> Sources.
STABLE_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("yts", "YTS"),
    ("piratebay_stable", "The Pirate Bay"),
)

#: Stable APIs on by default. YTS is deliberately absent: yts.mx no longer
#: publishes an A record at all - not blocked, simply gone - so leaving it on
#: cost every search two 10-second connect timeouts before any results showed.
DEFAULT_STABLE_PROVIDERS: tuple[str, ...] = ("piratebay_stable",)

#: Vendored multi-site providers we recommend enabling by default.
#:
#: These must match the keys `site_configs()` actually returns. They previously
#: read "nyaaSi" and "magnet_dl", which match nothing, so Nyaa was never on by
#: default despite the intent - and Nyaa is one of the two sources that answer
#: reliably. MagnetDL is left out: magnetdl.com is the slowest probe by far.
DEFAULT_VENDOR_PROVIDERS: tuple[str, ...] = (
    "1337x",
    "tgx",
    "nyaasi",
)


def all_provider_choices() -> list[dict]:
    """List every provider the user can toggle, with display metadata."""
    choices: list[dict] = []
    for key, label in STABLE_PROVIDERS:
        choices.append({
            "key": key,
            "label": label,
            "kind": "stable",
            "defaultOn": key in DEFAULT_STABLE_PROVIDERS,
        })
    for key, cfg in site_configs().items():
        choices.append({
            "key": f"vendor:{key}",
            "label": cfg.get("name") or key,
            "kind": "vendor",
            "defaultOn": key in DEFAULT_VENDOR_PROVIDERS,
        })
    return choices


__all__ = [
    "available_sites",
    "site_configs",
    "STABLE_PROVIDERS",
    "DEFAULT_STABLE_PROVIDERS",
    "DEFAULT_VENDOR_PROVIDERS",
    "all_provider_choices",
]
