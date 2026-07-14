"""Per-chunk audio transcription via the OpenAI Whisper API.

The recorder writes chunks as raw 48kHz stereo WAV (Discord's native decode
format - see app/bot/recorder.py). A single chunk at that rate/format can be
tens of MB, uncomfortably close to (or over, for longer chunk intervals) the
Whisper API's per-file upload limit, and Whisper only needs 16kHz mono input
internally anyway. So each chunk is downsampled to mono 16kHz before upload.

This shells out to the `ffmpeg` binary (already a hard runtime requirement
of this app for Discord voice - see requirements.txt) rather than pulling in
an extra Python audio-processing dependency for one conversion.
"""
import logging
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    pass


def _downsample_to_mono_16k(wav_path: Path, out_path: Path) -> None:
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(wav_path),
            "-ac", "1",
            "-ar", "16000",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise TranscriptionError(
            f"ffmpeg failed to downsample {wav_path.name}: {result.stderr.strip()[-500:]}"
        )


def transcribe_chunk(wav_path: Path, client: OpenAI, model: str) -> str:
    """Transcribes a single per-user recording chunk and returns plain text.

    Raises TranscriptionError on any failure (missing ffmpeg, API error,
    unreadable file) so callers can decide how to handle a partial failure
    (e.g. skip this chunk but keep processing the rest of the session)
    rather than getting an opaque exception type.
    """
    if not wav_path.exists():
        raise TranscriptionError(f"Audio chunk not found: {wav_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        downsampled = Path(tmp_dir) / f"{wav_path.stem}_16k.wav"
        try:
            _downsample_to_mono_16k(wav_path, downsampled)
        except FileNotFoundError as exc:
            raise TranscriptionError(
                "ffmpeg was not found on PATH - it is required to prepare audio for "
                "transcription (see requirements.txt / risk #5)"
            ) from exc

        try:
            with open(downsampled, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model=model,
                    response_format="text",
                )
        except Exception as exc:  # OpenAI SDK raises various APIError subtypes
            raise TranscriptionError(f"Whisper transcription failed for {wav_path.name}: {exc}") from exc

    # response_format="text" returns a plain str; other formats return objects.
    return transcription if isinstance(transcription, str) else transcription.text
