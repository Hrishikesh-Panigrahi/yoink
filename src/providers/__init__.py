"""Provider list and on-by-default choices for Settings > Sources."""

from providers.torrent_api_py import available_sites, site_configs

STABLE_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("piratebay_stable", "The Pirate Bay"),
)

DEFAULT_STABLE_PROVIDERS: tuple[str, ...] = ("piratebay_stable",)

#: These must match the keys `site_configs()` returns.
DEFAULT_VENDOR_PROVIDERS: tuple[str, ...] = (
    "1337x",
    "nyaasi",
    "ybt",
)


def all_provider_choices() -> list[dict]:
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
