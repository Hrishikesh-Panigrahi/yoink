"""Tests for free_proxies, which finds a working free proxy from public lists."""

from __future__ import annotations

import requests
import responses

import free_proxies


def test_fetch_candidates_merges_and_dedupes_the_lists():
    with responses.RequestsMock() as mock:
        mock.add(responses.GET, free_proxies.LISTS[0], body="1.2.3.4:80\n5.6.7.8:8080\nnot a proxy\n")
        mock.add(responses.GET, free_proxies.LISTS[1], body="1.2.3.4:80\r\n9.9.9.9:3128\r\n")
        mock.add(responses.GET, free_proxies.LISTS[2], body=requests.ConnectionError("list is down"))

        assert sorted(free_proxies.fetch_candidates()) == ["1.2.3.4:80", "5.6.7.8:8080", "9.9.9.9:3128"]


@responses.activate
def test_check_accepts_a_real_api_answer():
    responses.add(responses.GET, free_proxies.WORKS_URL, json=[{"info_hash": "ab" * 20, "name": "Ubuntu"}])

    assert isinstance(free_proxies.check("1.2.3.4:80"), float)


@responses.activate
def test_check_rejects_anything_else():
    responses.add(responses.GET, free_proxies.WORKS_URL, body="<html>proxy login page</html>")

    assert free_proxies.check("1.2.3.4:80") is None


def _fake_network(monkeypatch, latencies, unblocked=()):
    monkeypatch.setattr(free_proxies, "check", lambda proxy, timeout=8.0: latencies[proxy])
    monkeypatch.setattr(free_proxies, "reaches_blocked_site", lambda proxy, timeout=12.0: proxy in unblocked)


def test_picks_a_proxy_that_gets_past_the_block_over_a_faster_one(monkeypatch):
    _fake_network(monkeypatch, {"a:1": 3.0, "b:2": 1.0, "c:3": None}, unblocked={"a:1"})

    found = free_proxies.find(candidates=["a:1", "b:2", "c:3"])

    assert found["proxy"] == "http://a:1"
    assert found["latency"] == 3.0
    assert found["reachesBlocked"] is True


def test_stops_at_the_first_proxy_that_gets_past_the_block(monkeypatch):
    candidates = [f"10.0.0.{n}:80" for n in range(50)]
    _fake_network(monkeypatch, dict.fromkeys(candidates, 1.0), unblocked={"10.0.0.7:80"})
    monkeypatch.setattr(free_proxies, "MAX_WORKING", len(candidates))

    found = free_proxies.find(candidates=candidates)

    assert found["proxy"] == "http://10.0.0.7:80"


def test_falls_back_to_the_fastest_working_proxy(monkeypatch):
    _fake_network(monkeypatch, {"a:1": 3.0, "b:2": 1.0})

    found = free_proxies.find(candidates=["a:1", "b:2"])

    assert found["proxy"] == "http://b:2"
    assert found["reachesBlocked"] is False


def test_none_when_nothing_answers(monkeypatch):
    _fake_network(monkeypatch, {"a:1": None, "b:2": None})

    assert free_proxies.find(candidates=["a:1", "b:2"]) is None


def test_stops_once_enough_proxies_work(monkeypatch):
    candidates = [f"10.0.0.{n}:80" for n in range(50)]
    _fake_network(monkeypatch, dict.fromkeys(candidates, 1.0))
    monkeypatch.setattr(free_proxies, "MAX_WORKING", 2)
    progress = []

    found = free_proxies.find(on_progress=lambda *counts: progress.append(counts), candidates=candidates)

    assert found["tested"] == 2
    assert progress[-1] == (2, 50, 2)


def test_gives_up_at_the_deadline_with_the_best_so_far(monkeypatch):
    _fake_network(monkeypatch, {"a:1": 2.0, "b:2": 1.0})
    monkeypatch.setattr(free_proxies, "DEADLINE_SECONDS", -1)

    found = free_proxies.find(candidates=["a:1", "b:2"])

    assert found["tested"] == 1
    assert found["reachesBlocked"] is False


def test_honours_a_stop_request(monkeypatch):
    _fake_network(monkeypatch, {"a:1": 1.0})

    assert free_proxies.find(should_stop=lambda: True, candidates=["a:1"]) is None
