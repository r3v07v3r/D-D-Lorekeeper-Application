"""Assembles a single speaker-tagged transcript for a session from the
per-user, per-chunk .wav files the recorder wrote to disk.

Filenames follow `user_{discord_id}_chunk_{index:04d}.wav` (see
app/bot/recorder.py). Because every user's recording chunk boundaries are
driven by the same session-wide timer (the whole VoiceClient is stopped and
restarted together, not per user), chunk index N for every user corresponds
to the same wall-clock window. That lets us approximate chronological order
by walking chunks in index order and, within a chunk, listing whichever
users spoke - without needing per-utterance timestamps, which Whisper's
plain-text response doesn't give us. A real per-utterance timeline would
need `response_format="verbose_json"` plus timestamp-based interleaving;
that's a reasonable future improvement, not attempted here.
"""
import logging
import re
from pathlib import Path

from openai import OpenAI
from sqlalchemy.orm import Session

from app.ai.transcription import TranscriptionError, transcribe_chunk
from app.models import User

logger = logging.getLogger(__name__)

_CHUNK_FILENAME_RE = re.compile(r"^user_(?P<discord_id>\d+)_chunk_(?P<index>\d+)\.wav$")


def _speaker_label(discord_id: str, discord_id_to_username: dict[str, str]) -> str:
    username = discord_id_to_username.get(discord_id)
    return username if username is not None else f"Unknown (discord id {discord_id})"


def build_session_transcript(session_dir: Path, db: Session, client: OpenAI, whisper_model: str) -> str:
    """Transcribes every chunk file under session_dir and returns one
    speaker-tagged transcript, ordered by chunk index.

    A chunk that fails to transcribe is noted inline rather than aborting
    the whole session - a few minutes of unusable audio (background noise,
    API hiccup) shouldn't discard hours of otherwise-good transcript.
    """
    discord_id_to_username = {
        user.discord_id: user.username for user in db.query(User).filter(User.discord_id.isnot(None))
    }

    chunks_by_index: dict[int, list[tuple[str, Path]]] = {}
    for path in sorted(session_dir.glob("user_*_chunk_*.wav")):
        match = _CHUNK_FILENAME_RE.match(path.name)
        if not match:
            continue
        index = int(match.group("index"))
        chunks_by_index.setdefault(index, []).append((match.group("discord_id"), path))

    lines: list[str] = []
    for index in sorted(chunks_by_index):
        for discord_id, path in sorted(chunks_by_index[index]):
            label = _speaker_label(discord_id, discord_id_to_username)
            try:
                text = transcribe_chunk(path, client, whisper_model).strip()
            except TranscriptionError as exc:
                logger.warning("Chunk transcription failed: %s", exc)
                lines.append(f"[{label}] <transcription failed for this segment>")
                continue
            if text:
                lines.append(f"[{label}] {text}")

    return "\n".join(lines)
