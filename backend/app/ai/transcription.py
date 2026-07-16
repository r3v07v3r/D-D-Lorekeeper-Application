"""Per-chunk audio transcription, via either the OpenAI Whisper API (paid,
hosted) or faster-whisper running locally (free - see
app/config.py:transcription_provider).

The recorder writes chunks as raw 48kHz stereo WAV (Discord's native decode
format - see app/bot/recorder.py). A single chunk at that rate/format can be
tens of MB, uncomfortably close to (or over, for longer chunk intervals) the
Whisper API's per-file upload limit, and Whisper only needs 16kHz mono input
internally anyway. So for the OpenAI path, each chunk is downsampled to mono
16kHz before upload. faster-whisper decodes audio itself (via ffmpeg/PyAV)
and handles resampling internally, so the local path skips this step and
transcribes the original chunk directly.

The downsample step shells out to the `ffmpeg` binary (already a hard
runtime requirement of this app for Discord voice - see requirements.txt)
rather than pulling in an extra Python audio-processing dependency for one
conversion.
"""
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from openai import OpenAI

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

    from app.config import Settings
    from app.runtime_config import RuntimeConfigStore

logger = logging.getLogger(__name__)

# faster-whisper model loads take a few seconds and hold the model weights in
# memory - reused across chunks/sessions rather than reloaded per call.
_local_model_cache: dict[str, "WhisperModel"] = {}


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


def _get_local_model(model_size: str) -> "WhisperModel":
    if model_size not in _local_model_cache:
        from faster_whisper import WhisperModel

        logger.info("Loading local Whisper model '%s' (first use downloads it, then caches on disk)", model_size)
        _local_model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _local_model_cache[model_size]


def _transcribe_local(wav_path: Path, model_size: str) -> str:
    try:
        model = _get_local_model(model_size)
        segments, _info = model.transcribe(str(wav_path))
        return " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:
        raise TranscriptionError(f"Local Whisper transcription failed for {wav_path.name}: {exc}") from exc


def _transcribe_openai(wav_path: Path, model: str, openai_api_key: str) -> str:
    client = OpenAI(api_key=openai_api_key)
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


def transcribe_chunk(wav_path: Path, settings: "Settings | RuntimeConfigStore") -> str:
    """Transcribes a single per-user recording chunk and returns plain text.

    Raises TranscriptionError on any failure (missing ffmpeg, API error,
    unreadable file, missing local model) so callers can decide how to
    handle a partial failure (e.g. skip this chunk but keep processing the
    rest of the session) rather than getting an opaque exception type.
    """
    if not wav_path.exists():
        raise TranscriptionError(f"Audio chunk not found: {wav_path}")

    if settings.transcription_provider == "local":
        return _transcribe_local(wav_path, settings.local_whisper_model_size)
    return _transcribe_openai(wav_path, settings.whisper_model, settings.openai_api_key)
