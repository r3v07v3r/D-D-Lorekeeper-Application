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
