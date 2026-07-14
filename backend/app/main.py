"""FastAPI application entrypoint.

Wires up the database, session store, and the Discord bot (as a background
asyncio task sharing this process's event loop, per the project's
single-process desktop architecture) then mounts all routers.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import SessionStore
from app.bot.client import create_bot
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.dndbeyond.sync import CharacterSyncState
from app.routers import auth, bot_control, characters, notes, sessions, users
from app.state import BotState

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


@app.on_event("startup")
async def on_startup() -> None:
    # Phase 1 uses create_all() directly; Alembic is deliberately not wired
    # up yet (project risk #6) until it's actually needed and set up for real.
    Base.metadata.create_all(bind=engine)

    app.state.sessions = SessionStore()

    bot_state = BotState()
    app.state.bot_state = bot_state

    if settings.discord_bot_token:
        bot = create_bot(bot_state)
        bot_state.bot = bot
        app.state.bot_task = asyncio.create_task(bot.start(settings.discord_bot_token))
    else:
        logger.warning("DISCORD_BOT_TOKEN not set - running API-only, the Discord bot will not start")
        app.state.bot_task = None

    dndbeyond_sync = CharacterSyncState()
    app.state.dndbeyond_sync = dndbeyond_sync
    dndbeyond_sync.start_background_sync(SessionLocal, settings.dndbeyond_sync_interval_minutes)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    bot_state: BotState = app.state.bot_state
    if bot_state.bot is not None:
        await bot_state.bot.close()
    bot_task = getattr(app.state, "bot_task", None)
    if bot_task is not None:
        bot_task.cancel()

    app.state.dndbeyond_sync.stop_background_sync()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
