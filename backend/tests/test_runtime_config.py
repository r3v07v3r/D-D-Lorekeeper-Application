"""Tests for RuntimeConfigStore: overrides layer on top of env defaults,
persist to disk, survive reloading, and reject unknown fields.
"""
import pytest

from app.config import Settings
from app.runtime_config import RuntimeConfigStore


@pytest.fixture
def base_settings():
    return Settings(
        discord_bot_token="",
        openai_api_key="",
        whisper_model="whisper-1",
        summarization_model="gpt-4o",
        recording_chunk_minutes=5,
        dndbeyond_sync_interval_minutes=15,
    )


def test_falls_back_to_base_when_no_overrides(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    assert store.whisper_model == "whisper-1"
    assert store.discord_bot_token == ""
    assert store.is_set("discord_bot_token") is False


def test_update_overrides_and_is_set_reflects_it(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.update(discord_bot_token="abc123", recording_chunk_minutes=10)

    assert store.discord_bot_token == "abc123"
    assert store.is_set("discord_bot_token") is True
    assert store.recording_chunk_minutes == 10
    # Untouched fields still fall back to base.
    assert store.whisper_model == "whisper-1"


def test_overrides_persist_across_instances(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.update(openai_api_key="sk-test", summarization_model="gpt-4o-mini")

    reloaded = RuntimeConfigStore(tmp_path, base=base_settings)
    assert reloaded.openai_api_key == "sk-test"
    assert reloaded.summarization_model == "gpt-4o-mini"


def test_update_ignores_none_values(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.update(discord_bot_token="abc123")
    store.update(discord_bot_token=None, openai_api_key="sk-test")

    # The None in the second update() call must not clobber the first value.
    assert store.discord_bot_token == "abc123"
    assert store.openai_api_key == "sk-test"


def test_update_rejects_unknown_field(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    with pytest.raises(ValueError):
        store.update(database_url="sqlite:///evil.db")


def test_non_editable_fields_fall_through_to_base(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    assert store.audio_storage_dir == base_settings.audio_storage_dir


def test_no_passphrase_set_by_default(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    assert store.has_passphrase() is False
    assert store.verify_passphrase("anything") is False
    assert store.verify_passphrase("") is False


def test_set_passphrase_verifies_correctly(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.set_passphrase("open-sesame")

    assert store.has_passphrase() is True
    assert store.verify_passphrase("open-sesame") is True
    assert store.verify_passphrase("wrong-phrase") is False
    assert store.verify_passphrase("") is False


def test_passphrase_never_stored_in_plaintext(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.set_passphrase("open-sesame")

    raw_contents = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "open-sesame" not in raw_contents


def test_passphrase_persists_across_instances(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.set_passphrase("open-sesame")

    reloaded = RuntimeConfigStore(tmp_path, base=base_settings)
    assert reloaded.has_passphrase() is True
    assert reloaded.verify_passphrase("open-sesame") is True


def test_setting_empty_passphrase_clears_it(tmp_path, base_settings):
    store = RuntimeConfigStore(tmp_path, base=base_settings)
    store.set_passphrase("open-sesame")
    store.set_passphrase("")

    assert store.has_passphrase() is False
    assert store.verify_passphrase("open-sesame") is False
