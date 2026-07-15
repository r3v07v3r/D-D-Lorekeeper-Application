"""Tests for app.netinfo's public IP caching (avoids hitting an external
service, or blocking on its timeout, on every Settings page load).
"""
import app.netinfo as netinfo


def test_caches_successful_result(monkeypatch):
    netinfo._public_ip_cache = None
    calls = []

    def fake_fetch():
        calls.append(1)
        return "203.0.113.5"

    monkeypatch.setattr(netinfo, "_fetch_public_ip", fake_fetch)

    assert netinfo.detect_public_ip() == "203.0.113.5"
    assert netinfo.detect_public_ip() == "203.0.113.5"
    assert len(calls) == 1  # second call served from cache, not re-fetched


def test_cache_expires_after_ttl(monkeypatch):
    netinfo._public_ip_cache = None
    calls = []

    def fake_fetch():
        calls.append(1)
        return "203.0.113.5"

    monkeypatch.setattr(netinfo, "_fetch_public_ip", fake_fetch)
    monkeypatch.setattr(netinfo, "_CACHE_TTL_SECONDS", 0)

    netinfo.detect_public_ip()
    netinfo.detect_public_ip()
    assert len(calls) == 2  # TTL of 0 means every call re-fetches


def test_failure_is_not_permanently_cached_as_none(monkeypatch):
    netinfo._public_ip_cache = None
    monkeypatch.setattr(netinfo, "_CACHE_TTL_SECONDS", 0)

    monkeypatch.setattr(netinfo, "_fetch_public_ip", lambda: None)
    assert netinfo.detect_public_ip() is None

    monkeypatch.setattr(netinfo, "_fetch_public_ip", lambda: "203.0.113.5")
    assert netinfo.detect_public_ip() == "203.0.113.5"
