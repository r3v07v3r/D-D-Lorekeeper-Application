"""Tests for the "setup outstanding" computation that powers the GM
dashboard's setup banner (see app/routers/settings.py:_compute_setup_items).
"""
import httpx
import pytest

from app.config import Settings
from app.routers import settings as settings_router
from app.runtime_config import RuntimeConfigStore


@pytest.fixture
def store(tmp_path):
    return RuntimeConfigStore(tmp_path, base=Settings())


@pytest.fixture(autouse=True)
def clear_ollama_cache():
    """_check_ollama_reachable caches per base_url (see settings.py) - several
    tests below share the same default base_url with different monkeypatched
    behavior, so a stale cache entry from a previous test would leak into the
    next one without this.
    """
    settings_router._ollama_reachable_cache.clear()
    yield
    settings_router._ollama_reachable_cache.clear()


def test_flags_missing_discord_token(store):
    items = settings_router._compute_setup_items(store)
    keys = [i.key for i in items]
    assert "discord_bot_token" in keys
    assert next(i for i in items if i.key == "discord_bot_token").severity == "required"


def test_no_discord_flag_once_token_set(store):
    store.update(discord_bot_token="abc123")
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "discord_bot_token" not in keys


def test_flags_missing_openai_key_when_selected_for_either_stage(store, monkeypatch):
    store.update(discord_bot_token="abc123", transcription_provider="openai", llm_provider="ollama")
    monkeypatch.setattr(settings_router.httpx, "get", lambda url, timeout: (_ for _ in ()).throw(httpx.ConnectError("stub")))
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "openai_api_key" in keys


def test_no_openai_flag_when_both_stages_use_free_providers(store, monkeypatch):
    store.update(
        discord_bot_token="abc123",
        transcription_provider="local",
        llm_provider="ollama",
    )
    # Not testing Ollama reachability here - stub it out so this doesn't make
    # a real (slow, flaky-in-CI) network call to an address that's likely
    # unreachable in a test environment anyway.
    monkeypatch.setattr(settings_router.httpx, "get", lambda url, timeout: (_ for _ in ()).throw(httpx.ConnectError("stub")))
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "openai_api_key" not in keys


def test_no_openai_flag_when_key_is_set(store):
    store.update(discord_bot_token="abc123", llm_provider="openai", openai_api_key="sk-test")
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "openai_api_key" not in keys


def test_flags_unreachable_ollama(store, monkeypatch):
    store.update(discord_bot_token="abc123", llm_provider="ollama")

    def fake_get(url, timeout):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(settings_router.httpx, "get", fake_get)
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "ollama" in keys


def test_no_ollama_flag_when_reachable(store, monkeypatch):
    store.update(discord_bot_token="abc123", llm_provider="ollama")

    def fake_get(url, timeout):
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(settings_router.httpx, "get", fake_get)
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "ollama" not in keys


def test_flags_missing_passphrase_as_optional(store):
    items = settings_router._compute_setup_items(store)
    passphrase_item = next(i for i in items if i.key == "campaign_passphrase")
    assert passphrase_item.severity == "optional"


def test_no_passphrase_flag_once_set(store):
    store.set_passphrase("open-sesame")
    keys = [i.key for i in settings_router._compute_setup_items(store)]
    assert "campaign_passphrase" not in keys


def test_ollama_reachability_is_cached_per_base_url(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(settings_router.httpx, "get", fake_get)

    first = settings_router._check_ollama_reachable("http://localhost:11434/v1")
    second = settings_router._check_ollama_reachable("http://localhost:11434/v1")

    assert first is True
    assert second is True
    assert len(calls) == 1  # second call served from cache, no new network call


def test_ollama_reachability_cache_is_keyed_per_base_url(monkeypatch):
    def fake_get(url, timeout):
        if "11434" in url:
            return httpx.Response(200, request=httpx.Request("GET", url))
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(settings_router.httpx, "get", fake_get)

    assert settings_router._check_ollama_reachable("http://localhost:11434/v1") is True
    assert settings_router._check_ollama_reachable("http://localhost:9999/v1") is False


def test_fully_configured_local_setup_has_no_required_items(store, monkeypatch):
    store.update(
        discord_bot_token="abc123",
        transcription_provider="local",
        llm_provider="ollama",
    )
    store.set_passphrase("open-sesame")

    def fake_get(url, timeout):
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(settings_router.httpx, "get", fake_get)
    items = settings_router._compute_setup_items(store)
    assert items == []
