"""Persisted, GM-editable settings that layer on top of the env-based
Settings (app/config.py).

Why this exists: a packaged, single-file Electron build has no editable
.env sitting next to it, so there needs to be an in-app way for the GM to
enter a Discord bot token and OpenAI API key without touching a text file.
Env vars / .env remain the mechanism for developer/advanced use and for
settings that aren't safe to flip at runtime (DATABASE_URL, AUDIO_STORAGE_DIR,
CORS_ORIGINS); this store only covers the fields a GM should reasonably be
able to change from a Settings screen.

Persistence location: a JSON file under `config_dir`, which Electron points
at `app.getPath('userData')` (a stable per-user directory that survives
app reinstalls/updates) - see electron/main.js. In dev, it defaults to the
backend's own working directory.
"""
import hashlib
import json
import logging
import secrets
from pathlib import Path
from threading import Lock

from fastapi import Request

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_PBKDF2_ITERATIONS = 200_000

# The only fields editable via the Settings API/UI - deliberately a subset
# of Settings, not all of it (see module docstring for why).
EDITABLE_FIELDS = (
    "discord_bot_token",
    "openai_api_key",
    "whisper_model",
    "summarization_model",
    "recording_chunk_minutes",
    "dndbeyond_sync_interval_minutes",
)

# Fields containing secrets - never echoed back verbatim by the API.
SECRET_FIELDS = ("discord_bot_token", "openai_api_key")


class RuntimeConfigStore:
    def __init__(self, config_dir: Path, base: Settings | None = None) -> None:
        self._path = Path(config_dir) / "settings.json"
        self._base = base or get_settings()
        self._overrides: dict = {}
        self._lock = Lock()
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._overrides = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read %s, starting with no overrides: %s", self._path, exc)
                self._overrides = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._overrides, indent=2), encoding="utf-8")

    def update(self, **kwargs) -> None:
        """Merges only non-None, known fields and persists to disk."""
        with self._lock:
            for key, value in kwargs.items():
                if key not in EDITABLE_FIELDS:
                    raise ValueError(f"Unknown or non-editable setting: {key}")
                if value is not None:
                    self._overrides[key] = value
            self._save()

    def is_set(self, field: str) -> bool:
        value = getattr(self, field)
        return bool(value)

    # ---- Campaign passphrase ----
    #
    # Gates the only two unauthenticated endpoints (GET /users, POST
    # /auth/login) once the backend is reachable from more than just the
    # GM's own machine (see app.auth.require_network_access). Stored
    # salted+hashed via PBKDF2, never in plaintext - unlike the other
    # secrets above (Discord token, OpenAI key), which the app itself needs
    # to present verbatim to a third-party API and so cannot be one-way
    # hashed.

    def set_passphrase(self, raw: str) -> None:
        with self._lock:
            if not raw:
                self._overrides.pop("campaign_passphrase_hash", None)
            else:
                salt = secrets.token_hex(16)
                digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS).hex()
                self._overrides["campaign_passphrase_hash"] = f"{salt}${digest}"
            self._save()

    def has_passphrase(self) -> bool:
        return bool(self._overrides.get("campaign_passphrase_hash"))

    def verify_passphrase(self, raw: str) -> bool:
        stored = self._overrides.get("campaign_passphrase_hash")
        if not stored or "$" not in stored:
            return False
        salt, _, expected_digest = stored.partition("$")
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256", (raw or "").encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
        ).hex()
        return secrets.compare_digest(actual_digest, expected_digest)

    def __getattr__(self, name: str):
        # Only called for attributes not found normally - i.e. anything not
        # already defined on this instance, which is exactly what we want:
        # editable fields resolve override-or-base, everything else falls
        # through to the immutable env-based Settings.
        if name in EDITABLE_FIELDS:
            return self._overrides.get(name, getattr(self._base, name))
        return getattr(self._base, name)


def get_runtime_config(request: Request) -> "RuntimeConfigStore":
    return request.app.state.runtime_config
