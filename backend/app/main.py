"""FastAPI application entrypoint.

Wires up the database, session store, and the Discord bot (as a background
asyncio task sharing this process's event loop, per the project's
single-process desktop architecture) then mounts all routers.
"""
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import SessionStore
from app.bot.client import ensure_bot_running
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.dndbeyond.sync import CharacterSyncState
from app.routers import auth, bot_control, characters, notes, sessions, settings as settings_router, soundboard, users
from app.runtime_config import RuntimeConfigStore
from app.state import BotState
from app.tls import ensure_certificate, get_fingerprint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lorekeeper API")

settings = get_settings()

# NOTE (risk #8): "null" must be in cors_origins for the packaged Electron
# app to work - verified directly against this middleware (see config.py).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(notes.router)
app.include_router(bot_control.router)
app.include_router(characters.router)
app.include_router(settings_router.router)
app.include_router(soundboard.router)


@app.on_event("startup")
async def on_startup() -> None:
    # Phase 1 uses create_all() directly; Alembic is deliberately not wired
    # up yet (project risk #6) until it's actually needed and set up for real.
    Base.metadata.create_all(bind=engine)

    app.state.sessions = SessionStore()

    bot_state = BotState()
    app.state.bot_state = bot_state

    # Electron points this at app.getPath('userData') so a GM's saved
    # settings (Discord token, OpenAI key, etc. - see app/runtime_config.py)
    # survive app reinstalls/updates. Defaults to the working directory for
    # local/dev use.
    config_dir = Path(os.environ.get("LOREKEEPER_CONFIG_DIR", "."))
    runtime_config = RuntimeConfigStore(config_dir, base=settings)
    app.state.runtime_config = runtime_config

    # run.py already generated this (it has to, to pass ssl_certfile/keyfile
    # to uvicorn before the app even starts) - ensure_certificate is
    # idempotent, so calling it again here just returns the same paths, and
    # gives this module a self-contained way to know the fingerprint to
    # expose via Settings without run.py having to pass it through.
    cert_path, _key_path = ensure_certificate(config_dir)
    app.state.tls_fingerprint = get_fingerprint(cert_path)

    if not runtime_config.discord_bot_token:
        logger.warning("No Discord bot token configured yet - running API-only until one is set via Settings")
    await ensure_bot_running(bot_state, runtime_config.discord_bot_token)

    dndbeyond_sync = CharacterSyncState()
    app.state.dndbeyond_sync = dndbeyond_sync
    dndbeyond_sync.start_background_sync(SessionLocal, runtime_config.dndbeyond_sync_interval_minutes)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    bot_state: BotState = app.state.bot_state
    if bot_state.bot is not None:
        await bot_state.bot.close()
    if bot_state.bot_task is not None:
        bot_state.bot_task.cancel()

    app.state.dndbeyond_sync.stop_background_sync()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
