"""Validation and disk storage for GM soundboard clips - kept separate from
the router so the validation logic (extension allow-list, size limit) is
plain, easily-testable functions with no FastAPI/DB involved.
"""
import base64
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
MAX_CLIP_BYTES = 8 * 1024 * 1024  # 8MB - generous for a short sound effect

# For local (non-bot) playback in the renderer - see
# app/routers/soundboard.py:get_clip_audio. m4a's actual container is MP4
# audio; "audio/mp4" is the widely-supported HTML5 <audio> MIME type for it,
# not "audio/m4a" (not a registered type browsers reliably recognize).
MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
}


class SoundClipError(Exception):
    """Raised for any invalid upload (bad extension, too large, corrupt
    base64) so the router can turn it into a 400 with a clear message.
    """


def validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise SoundClipError(
            f"Unsupported file type '{ext or '(none)'}' - allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def decode_clip(content_base64: str) -> bytes:
    try:
        data = base64.b64decode(content_base64, validate=True)
    except ValueError as exc:  # covers binascii.Error, a ValueError subclass
        raise SoundClipError("Could not decode uploaded audio data") from exc
    if not data:
        raise SoundClipError("Uploaded file is empty")
    if len(data) > MAX_CLIP_BYTES:
        raise SoundClipError(f"File too large - max {MAX_CLIP_BYTES // (1024 * 1024)}MB per clip")
    return data


def save_clip_file(storage_dir: Path, extension: str, data: bytes) -> str:
    """Writes the clip under a generated name (not the user's original
    filename) so two uploads can never collide, and returns that filename.
    """
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    (storage_dir / filename).write_bytes(data)
    return filename


def delete_clip_file(storage_dir: Path, filename: str) -> None:
    path = storage_dir / filename
    if path.exists():
        path.unlink()
