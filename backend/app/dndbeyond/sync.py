"""Periodic background sync of every registered player's D&D Beyond
character, written into the same `characters` table (see app/models.py)
that manual character entry also writes to - see app/routers/characters.py.

Mirrors the pattern used for BotState/VoiceRecorder: a small state object
shared via app.state, refreshed by a periodic asyncio task rather than
fetched synchronously per-request (fetching from D&D Beyond on every
dashboard load would be slow and easy to rate-limit). `errors` stays
in-memory (transient per-attempt status, not part of the character record
itself); the character data itself is persisted, not cached in memory.
"""
import asyncio
import logging

from sqlalchemy.orm import Session

from app.dndbeyond.parser import fetch_and_parse_character
from app.models import Character, User

logger = logging.getLogger(__name__)


class CharacterSyncState:
    def __init__(self) -> None:
        self.errors: dict[int, str] = {}  # keyed by our User.id
        self._task: asyncio.Task | None = None

    async def sync_once(self, db: Session) -> None:
        players = db.query(User).filter(User.dnd_beyond_character_id.isnot(None)).all()
        for user in players:
            try:
                parsed = await fetch_and_parse_character(user.dnd_beyond_character_id)
            except Exception as exc:
                logger.warning("D&D Beyond sync failed for user %s: %s", user.username, exc)
                self.errors[user.id] = str(exc)
                continue

            character = db.query(Character).filter(Character.user_id == user.id).one_or_none()
            if character is None:
                character = Character(user_id=user.id, source="dndbeyond")
                db.add(character)
            character.source = "dndbeyond"
            character.name = parsed.name
            character.race = parsed.race
            character.classes = parsed.classes
            character.level = parsed.level
            character.proficiency_bonus = parsed.proficiency_bonus
            character.ability_scores = parsed.ability_scores
            character.hp_current = parsed.hp_current
            character.hp_max = parsed.hp_max
            character.hp_temp = parsed.hp_temp
            character.armor_class = parsed.armor_class
            character.armor_class_is_estimate = parsed.armor_class_is_estimate
            character.passive_perception = parsed.passive_perception
            character.passive_perception_is_estimate = parsed.passive_perception_is_estimate
            character.currencies = parsed.currencies
            character.inventory = [
                {"name": item.name, "quantity": item.quantity, "equipped": item.equipped} for item in parsed.inventory
            ]
            # D&D Beyond's character parser (app/dndbeyond/parser.py) doesn't
            # parse spell data - deliberately not attempted here either (kept
            # lean, see project scope). Leaves spell_slots/known_spells
            # untouched rather than clobbering whatever the player has
            # tracked manually on each sync.
            db.commit()
            self.errors.pop(user.id, None)

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
