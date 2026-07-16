"""Pydantic request/response schemas.

Deliberately excluded from client-writable fields: anything used for
authorization decisions (author_id, viewer identity/role, include_private
flags). Those are always derived server-side from the session token - see
app/auth.py.
"""
from datetime import date as date_type
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["gm", "player"]


# ---- Users ----

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    discord_id: str | None = None
    dnd_beyond_character_id: str | None = None


class UserCreate(BaseModel):
    username: str
    role: Role
    discord_id: str | None = None
    dnd_beyond_character_id: str | None = None


# ---- Auth ----

class LoginRequest(BaseModel):
    user_id: int


class LoginResponse(BaseModel):
    token: str
    user: UserPublic


# ---- Session logs ----

class SessionLogCreate(BaseModel):
    campaign_name: str
    session_number: int
    date: date_type


class SessionLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_name: str
    session_number: int
    date: date_type
    full_transcript: str | None = None
    gm_summary: str | None = None
    player_summary: str | None = None
    processing_status: str = "pending"
    processing_error: str | None = None


# ---- Notes ----

class NoteCreate(BaseModel):
    content: str
    # Only meaningful when the caller is the GM - see routers/notes.py. A
    # non-GM caller attempting to set either of these is rejected, not
    # silently downgraded, so mistakes are visible rather than swallowed.
    is_private_gm: bool = False
    target_player_id: int | None = None


class NotePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    author_id: int
    content: str
    is_private_gm: bool
    target_player_id: int | None = None


# ---- Settings ----

class SettingsUpdate(BaseModel):
    """All fields optional - PUT /settings only changes what's provided.
    Secrets are write-only: there is no way to read a previously-saved
    token/key/passphrase back out (see SettingsPublic), only to overwrite it.
    """
    discord_bot_token: str | None = None
    openai_api_key: str | None = None
    whisper_model: str | None = None
    summarization_model: str | None = None
    llm_provider: str | None = None
    ollama_base_url: str | None = None
    transcription_provider: str | None = None
    local_whisper_model_size: str | None = None
    recording_chunk_minutes: int | None = None
    dndbeyond_sync_interval_minutes: int | None = None
    campaign_passphrase: str | None = None


class SetupItem(BaseModel):
    """One thing the GM hasn't finished configuring yet - see
    app/routers/settings.py:_compute_setup_items(). "required" items mean a
    core feature (recording, transcription, summarization) won't work at all;
    "optional" items are fine to leave for solo/local-only play.
    """
    key: str
    severity: str  # "required" | "optional"
    message: str


class SettingsPublic(BaseModel):
    discord_bot_token_set: bool
    openai_api_key_set: bool
    whisper_model: str
    summarization_model: str
    llm_provider: str
    ollama_base_url: str
    transcription_provider: str
    local_whisper_model_size: str
    recording_chunk_minutes: int
    dndbeyond_sync_interval_minutes: int
    bot_running: bool
    campaign_passphrase_set: bool
    detected_lan_ip: str | None = None
    detected_public_ip: str | None = None
    certificate_fingerprint: str
    server_port: int
    setup_items: list[SetupItem]


# ---- Soundboard ----

class SoundClipUpload(BaseModel):
    """Uploaded as base64 JSON rather than multipart/form-data: the packaged
    app's requests are proxied through Electron's main process over IPC
    (see frontend/src/api/client.ts), which only carries a string body, not
    a real multipart stream. Clips are short sound effects, so the ~33%
    base64 overhead is a fine trade for keeping one request path for
    everything rather than a special case for file uploads.
    """
    name: str
    filename: str  # original filename, used only to read the extension
    content_base64: str
    volume: float = 1.0


class SoundClipUpdate(BaseModel):
    name: str | None = None
    volume: float | None = None


class SoundClipPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    volume: float
    created_at: datetime
