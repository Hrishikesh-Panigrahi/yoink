"""Tests for `utils.resolver`, the DNS-over-HTTPS resolver.

`_query` is stubbed, so no real DNS queries are made.
"""

from __future__ import annotations

import socket

import pytest

from utils import resolver


@pytest.fixture(autouse=True)
def clean_resolver():
    """`install()` patches the global `socket.getaddrinfo`, so always undo it."""
    resolver.uninstall()
    resolver.clear_cache()
    yield
    resolver.uninstall()
    resolver.clear_cache()


@pytest.fixture
def answers(monkeypatch):
    """Stub DoH with canned answers and return the list of hosts it was asked."""
    asked = []
    table = {"1337x.to": ["172.67.188.67", "104.21.40.193"]}

    def fake_query(host):
        asked.append(host)
        return list(table.get(host, []))

    monkeypatch.setattr(resolver, "_query", fake_query)
    return asked


# Lookup


def test_lookup_returns_the_addresses(answers):
    assert resolver.lookup("1337x.to") == ["172.67.188.67", "104.21.40.193"]


def test_lookup_is_cached(answers):
    resolver.lookup("1337x.to")
    resolver.lookup("1337x.to")

    assert answers == ["1337x.to"], "the second lookup should have hit the cache"


def test_lookup_caches_a_negative_answer_too(answers):
    assert resolver.lookup("gone.example") == []
    assert resolver.lookup("gone.example") == []
    assert answers == ["gone.example"]


def test_clear_cache_forces_a_fresh_query(answers):
    resolver.lookup("1337x.to")
    resolver.clear_cache()
    resolver.lookup("1337x.to")

    assert len(answers) == 2


def test_cache_expires(answers, monkeypatch):
    monkeypatch.setattr(resolver, "CACHE_TTL_SECONDS", -1)

    resolver.lookup("1337x.to")
    resolver.lookup("1337x.to")

    assert len(answers) == 2


def test_lookup_never_resolves_its_own_resolvers(answers):
    # Resolving a DoH endpoint through DoH would loop forever.
    for host in resolver._RESOLVER_HOSTS:
        assert resolver.lookup(host) == []
    assert answers == []


def test_lookup_ignores_blank_input(answers):
    assert resolver.lookup("") == []
    assert resolver.lookup("   ") == []
    assert answers == []


def test_lookup_strips_a_trailing_dot(answers):
    resolver.lookup("1337x.to.")

    assert answers == ["1337x.to"]


# Address literals


@pytest.mark.parametrize(
    "value, expected",
    [
        ("127.0.0.1", True),
        ("8.8.8.8", True),
        ("::1", True),
        ("localhost", True),
        ("1337x.to", False),
        ("example.com", False),
    ],
)
def test_looks_like_an_address(value, expected):
    assert resolver._looks_like_an_address(value) is expected


# Installation


def test_install_replaces_getaddrinfo_and_uninstall_restores_it():
    original = socket.getaddrinfo

    resolver.install()
    assert socket.getaddrinfo is not original
    assert resolver.is_installed() is True

    resolver.uninstall()
    assert socket.getaddrinfo is original
    assert resolver.is_installed() is False


def test_install_is_idempotent():
    resolver.install()
    patched = socket.getaddrinfo
    resolver.install()

    assert socket.getaddrinfo is patched


def test_uninstall_without_install_is_harmless():
    original = socket.getaddrinfo

    resolver.uninstall()

    assert socket.getaddrinfo is original


def test_resolution_uses_the_doh_answer(answers):
    resolver.install()

    results = socket.getaddrinfo("1337x.to", 443, socket.AF_INET)

    assert [entry[4][0] for entry in results] == ["172.67.188.67", "104.21.40.193"]
    assert all(entry[4][1] == 443 for entry in results)
    assert all(entry[0] == socket.AF_INET for entry in results)


def test_resolution_falls_back_to_the_system_when_doh_has_nothing(answers, monkeypatch):
    calls = []
    real = resolver._system_getaddrinfo
    monkeypatch.setattr(
        resolver,
        "_system_getaddrinfo",
        lambda *a, **k: (calls.append(a[0]), real(*a, **k))[1],
    )
    resolver.install()

    socket.getaddrinfo("localhost", 80)

    assert calls == ["localhost"]


def test_a_failing_lookup_does_not_break_resolution(monkeypatch):
    def explode(host):
        raise RuntimeError("DoH endpoint unreachable")

    monkeypatch.setattr(resolver, "_query", explode)
    resolver.install()

    assert socket.getaddrinfo("localhost", 80)


def test_ipv6_requests_are_left_to_the_system(answers):
    resolver.install()

    try:
        socket.getaddrinfo("1337x.to", 443, socket.AF_INET6)
    except OSError:
        pass  # the system may have no AAAA record, only the route matters here

    assert answers == [], "an AF_INET6 request should not consult the A-record path"


# Settings


def test_apply_from_settings_follows_the_stored_value(monkeypatch):
    import db

    stored = {"dns_over_https_enabled": "0"}
    monkeypatch.setattr(db, "get_setting", lambda key: stored.get(key))
    assert resolver.apply_from_settings() is False
    assert resolver.is_installed() is False

    stored["dns_over_https_enabled"] = "1"
    assert resolver.apply_from_settings() is True
    assert resolver.is_installed() is True


def test_apply_from_settings_defaults_to_on(monkeypatch):
    import db

    monkeypatch.setattr(db, "get_setting", lambda key: None)

    assert resolver.apply_from_settings() is True
