"""Tests for the chunk-ordering/speaker-labeling logic in transcript_builder,
independent of any real OpenAI call (transcribe_chunk is monkeypatched).
"""
import datetime
import wave
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.ai.transcript_builder as transcript_builder
from app.database import Base
from app.models import User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    session.add_all(
        [
            User(username="alice", role="player", discord_id="111"),
            User(username="bob", role="player", discord_id="222"),
        ]
    )
    session.commit()
    yield session
    session.close()


def _touch_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(48000)
        f.writeframes(b"\x00\x00" * 100)


def test_orders_by_chunk_index_and_labels_known_and_unknown_speakers(db, monkeypatch, tmp_path):
    session_dir = tmp_path / "session_1"
    session_dir.mkdir()

    # chunk 0: alice speaks; chunk 1: bob and an unregistered discord user speak
    _touch_wav(session_dir / "user_111_chunk_0000.wav")
    _touch_wav(session_dir / "user_222_chunk_0001.wav")
    _touch_wav(session_dir / "user_999_chunk_0001.wav")

    def fake_transcribe_chunk(wav_path, client, model):
        return {
            "user_111_chunk_0000.wav": "Hello, I open the door.",
            "user_222_chunk_0001.wav": "I follow behind.",
            "user_999_chunk_0001.wav": "Who goes there?",
        }[wav_path.name]

    monkeypatch.setattr(transcript_builder, "transcribe_chunk", fake_transcribe_chunk)

    result = transcript_builder.build_session_transcript(session_dir, db, client=None, whisper_model="whisper-1")

    lines = result.split("\n")
    assert lines[0] == "[alice] Hello, I open the door."
    # chunk 1 has two speakers - both must appear, order between them is by discord_id sort
    assert "[bob] I follow behind." in lines[1:]
    assert "[Unknown (discord id 999)] Who goes there?" in lines[1:]


def test_failed_chunk_is_noted_inline_and_does_not_abort(db, monkeypatch, tmp_path):
    session_dir = tmp_path / "session_2"
    session_dir.mkdir()
    _touch_wav(session_dir / "user_111_chunk_0000.wav")
    _touch_wav(session_dir / "user_111_chunk_0001.wav")

    def fake_transcribe_chunk(wav_path, client, model):
        if "0000" in wav_path.name:
            raise transcript_builder.TranscriptionError("boom")
        return "second chunk text"

    monkeypatch.setattr(transcript_builder, "transcribe_chunk", fake_transcribe_chunk)

    result = transcript_builder.build_session_transcript(session_dir, db, client=None, whisper_model="whisper-1")

    assert "<transcription failed for this segment>" in result
    assert "second chunk text" in result
