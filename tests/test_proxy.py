"""Tests for utils.proxy, the Settings > Advanced proxy."""

from __future__ import annotations

from urllib.request import ProxyHandler, build_opener

import aiohttp.helpers
import pytest
import requests

from utils import proxy, resolver


@pytest.fixture(autouse=True)
def clean_proxy(monkeypatch):
    for key in proxy._ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(proxy, "_original", None)
    monkeypatch.setattr(proxy, "_active", "")
    monkeypatch.setattr(proxy, "_user_agent", "")


@pytest.mark.parametrize("given, expected", [
    ("  203.0.113.7:8080 ", "http://203.0.113.7:8080"),
    ("https://proxy.example:443", "https://proxy.example:443"),
    ("", ""),
])
def test_normalize(given, expected):
    assert proxy.normalize(given) == expected


@pytest.mark.parametrize("url", ["socks5://203.0.113.7:1080", "ftp://203.0.113.7:21", "http://203.0.113.7"])
def test_urls_it_cannot_use(url):
    assert proxy.problem_with(url)


@pytest.mark.parametrize("url", ["", "http://203.0.113.7:8080", "https://user:pass@proxy.example:8443"])
def test_urls_it_can_use(url):
    assert proxy.problem_with(url) is None


def test_requests_and_aiohttp_pick_up_the_proxy():
    assert proxy.apply("203.0.113.7:8080") is None

    assert requests.utils.get_environ_proxies("https://apibay.org")["https"] == "http://203.0.113.7:8080"
    assert str(aiohttp.helpers.proxies_from_env()["https"].proxy) == "http://203.0.113.7:8080"
    assert requests.utils.get_environ_proxies("http://localhost:9222") == {}
    assert proxy.active() == "http://203.0.113.7:8080"


def test_clearing_it_puts_back_a_system_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://corporate.example:3128")

    proxy.apply("http://203.0.113.7:8080")
    proxy.apply("")

    assert requests.utils.get_environ_proxies("https://apibay.org")["https"] == "http://corporate.example:3128"
    assert proxy.active() == ""


def test_a_bad_url_changes_nothing():
    proxy.apply("http://203.0.113.7:8080")

    assert proxy.apply("socks5://203.0.113.9:1080")
    assert proxy.active() == "http://203.0.113.7:8080"


def test_custom_user_agent():
    assert proxy.user_agent("Default/1.0") == "Default/1.0"
    proxy.apply("", "  Yoink/2.0  ")
    assert proxy.user_agent("Default/1.0") == "Yoink/2.0"


def test_dns_over_https_skips_the_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://203.0.113.7:8080")

    def proxied(opener):
        return any(isinstance(h, ProxyHandler) and h.proxies for h in opener.handlers)

    assert proxied(build_opener())
    assert not proxied(resolver._direct)
