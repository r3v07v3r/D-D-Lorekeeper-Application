"""Periodic background sync of every registered player's D&D Beyond
character, cached in memory (no new DB table - the project schema, Section
4, only defines Users.dnd_beyond_character_id, not a character-snapshot
table, so this deliberately doesn't add one).

Mirrors the pattern used for BotState/VoiceRecorder: a small state object
shared via app.state, refreshed by a periodic asyncio task rather than
fetched synchronously per-request (fetching from D&D Beyond on every
dashboard load would be slow and easy to rate-limit).
"""
import asyncio
import logging

from sqlalchemy.orm import Session

from app.dndbeyond.parser import ParsedCharacter, fetch_and_parse_character
from app.models import User

logger = logging.getLogger(__name__)


class CharacterSyncState:
    def __init__(self) -> None:
        self.characters: dict[int, ParsedCharacter] = {}  # keyed by our User.id
        self.errors: dict[int, str] = {}
        self._task: asyncio.Task | None = None

    async def sync_once(self, db: Session) -> None:
        players = db.query(User).filter(User.dnd_beyond_character_id.isnot(None)).all()
        for user in players:
            try:
                self.characters[user.id] = await fetch_and_parse_character(user.dnd_beyond_character_id)
                self.errors.pop(user.id, None)
            except Exception as exc:
                logger.warning("D&D Beyond sync failed for user %s: %s", user.username, exc)
                self.errors[user.id] = str(exc)

    def start_background_sync(self, session_factory, interval_minutes: int) -> None:
        async def _loop() -> None:
            while True:
                db = session_factory()
                try:
                    await self.sync_once(db)
                finally:
                    db.close()
                await asyncio.sleep(interval_minutes * 60)

        self._task = asyncio.create_task(_loop())

    def stop_background_sync(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
