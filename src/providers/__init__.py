"""Per-source torrent search adapters.

Import the concrete adapter modules directly
(`from providers.yts import search_yts`) — this package intentionally
avoids re-exports to prevent circular imports with `search/`.
"""

from providers.torrent_api_py import available_sites, site_configs

__all__ = ["available_sites", "site_configs"]
