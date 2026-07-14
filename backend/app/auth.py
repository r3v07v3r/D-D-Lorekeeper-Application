"""Server-side session auth.

Design (project spec Section 3): the client never supplies its own identity
or role for authorization purposes. On login it receives an opaque bearer
token; every subsequent request resolves that token, server-side, to a
(user_id, role) pair via SessionStore. Endpoints depend on get_current_user
(or require_gm) to obtain that identity - they must never read user_discord_id,
role, include_private, etc. from query params or the request body and treat
that as authoritative. This directly replaces the first-draft bug where
GET /sessions/{id}/notes accepted user_discord_id/include_private as plain
query parameters.

The store is in-memory and keyed by a random token. That's sufficient for a
local, single-machine desktop app: it doesn't need to survive a backend
restart, and restarting the server naturally invalidates all sessions.
"""
import secrets
from dataclasses import dataclass
from threading import Lock

from fastapi import Depends, Header, HTTPException, Request, status

from app.schemas import Role


@dataclass(frozen=True)
class SessionRecord:
    token: str
    user_id: int
    username: str
    role: Role


class SessionStore:
    """Thread-safe in-memory token -> SessionRecord store.

    A lock guards access because the Discord bot (running its own asyncio
    tasks) and FastAPI request handlers may touch this concurrently.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = Lock()

    def create(self, user_id: int, username: str, role: Role) -> SessionRecord:
        token = secrets.token_urlsafe(32)
        record = SessionRecord(token=token, user_id=user_id, username=username, role=role)
        with self._lock:
            self._sessions[token] = record
        return record

    def get(self, token: str) -> SessionRecord | None:
        with self._lock:
            return self._sessions.get(token)

    def delete(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    return authorization.split(" ", 1)[1].strip()


def get_session_store(request: Request) -> SessionStore:
    """Fetches the single shared SessionStore off app.state."""
    return request.app.state.sessions


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> SessionRecord:
    token = _extract_bearer_token(authorization)
    store: SessionStore = get_session_store(request)
    session = store.get(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    return session


def require_gm(current: SessionRecord = Depends(get_current_user)) -> SessionRecord:
    if current.role != "gm":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the GM role",
        )
    return current
