from torrents.libgen import Libgen
from torrents.nyaa_si import NyaaSi
from torrents.pirate_bay import PirateBay
from torrents.x1337 import x1337
from torrents.your_bittorrent import YourBittorrent

all_sites = {
    "1337x": {
        "website": x1337,
        "trending_available": True,
        "trending_category": True,
        "search_by_category": True,
        "recent_available": True,
        "recent_category_available": True,
        "categories": [
            "anime",
            "music",
            "games",
            "tv",
            "apps",
            "documentaries",
            "other",
            "xxx",
            "movies",
        ],
        "limit": 100,
    },
    "nyaasi": {
        "website": NyaaSi,
        "trending_available": False,
        "trending_category": False,
        "search_by_category": False,
        "recent_available": True,
        "recent_category_available": False,
        "categories": [],
        "limit": 50,
    },
    "piratebay": {
        "website": PirateBay,
        "trending_available": True,
        "trending_category": False,
        "search_by_category": False,
        "recent_available": True,
        "recent_category_available": True,
        "categories": ["tv"],
        "limit": 50,
    },
    "libgen": {
        "website": Libgen,
        "trending_available": False,
        "trending_category": False,
        "search_by_category": False,
        "recent_available": False,
        "recent_category_available": False,
        "categories": [],
        "limit": 25,
    },
    "ybt": {
        "website": YourBittorrent,
        "trending_available": True,
        "trending_category": True,
        "search_by_category": False,
        "recent_available": True,
        "recent_category_available": True,
        "categories": [
            "anime",
            "music",
            "games",
            "tv",
            "apps",
            "xxx",
            "movies",
            "books",
            "pictures",
            "other",
        ],  # book -> ebooks
        "limit": 20,
    },
}

sites_config = {
    key: {
        **site_info, 
        "website": site_info["website"]._name
    } for key, site_info in all_sites.items()
}

def check_if_site_available(site):
    if site in all_sites.keys():
        return all_sites
    return False
