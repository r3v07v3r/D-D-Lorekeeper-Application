"""Tests for provider-switching logic added for free/local alternatives to
OpenAI: Ollama for summarization, faster-whisper for transcription (see
app/config.py's llm_provider/transcription_provider). These don't hit a real
Ollama server or download a real Whisper model - they only verify that the
right code path/client configuration is chosen for each provider setting.
"""
from pathlib import Path

from app.ai import transcription
from app.ai.summarization import build_llm_client
from app.config import Settings


def test_build_llm_client_defaults_to_openai():
    settings = Settings(llm_provider="openai", openai_api_key="sk-test")
    client = build_llm_client(settings)
    assert client.api_key == "sk-test"
    assert "api.openai.com" in str(client.base_url)


def test_build_llm_client_uses_ollama_base_url():
    settings = Settings(llm_provider="ollama", ollama_base_url="http://localhost:11434/v1")
    client = build_llm_client(settings)
    assert str(client.base_url) == "http://localhost:11434/v1/"


def test_transcribe_chunk_routes_to_local_provider(monkeypatch, tmp_path):
    wav_path = tmp_path / "chunk.wav"
    wav_path.write_bytes(b"fake")
    settings = Settings(transcription_provider="local", local_whisper_model_size="tiny")

    calls = {}

    def fake_local(path: Path, model_size: str) -> str:
        calls["local"] = (path, model_size)
        return "local text"

    def fake_openai(path: Path, model: str, api_key: str) -> str:
        calls["openai"] = (path, model, api_key)
        return "openai text"

    monkeypatch.setattr(transcription, "_transcribe_local", fake_local)
    monkeypatch.setattr(transcription, "_transcribe_openai", fake_openai)

    result = transcription.transcribe_chunk(wav_path, settings)

    assert result == "local text"
    assert calls["local"] == (wav_path, "tiny")
    assert "openai" not in calls


def test_transcribe_chunk_routes_to_openai_provider(monkeypatch, tmp_path):
    wav_path = tmp_path / "chunk.wav"
    wav_path.write_bytes(b"fake")
    settings = Settings(transcription_provider="openai", whisper_model="whisper-1", openai_api_key="sk-test")

    calls = {}

    def fake_local(path: Path, model_size: str) -> str:
        calls["local"] = (path, model_size)
        return "local text"

    def fake_openai(path: Path, model: str, api_key: str) -> str:
        calls["openai"] = (path, model, api_key)
        return "openai text"

    monkeypatch.setattr(transcription, "_transcribe_local", fake_local)
    monkeypatch.setattr(transcription, "_transcribe_openai", fake_openai)

    result = transcription.transcribe_chunk(wav_path, settings)

    assert result == "openai text"
    assert calls["openai"] == (wav_path, "whisper-1", "sk-test")
    assert "local" not in calls


def test_transcribe_chunk_missing_file_raises_before_dispatch(tmp_path):
    settings = Settings(transcription_provider="local")
    try:
        transcription.transcribe_chunk(tmp_path / "missing.wav", settings)
        assert False, "expected TranscriptionError"
    except transcription.TranscriptionError as exc:
        assert "not found" in str(exc)
