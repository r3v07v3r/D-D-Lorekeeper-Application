"""Pydantic request/response schemas.

Deliberately excluded from client-writable fields: anything used for
authorization decisions (author_id, viewer identity/role, include_private
flags). Those are always derived server-side from the session token - see
app/auth.py.
"""
from datetime import date as date_type
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
