"""SQLAlchemy models: Users, SessionLogs, Notes, SoundClips, Characters,
Encounters/Combatants, RollLogEntries.
"""
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # "gm" or "player". Kept as a plain string (not a DB enum) so adding a role
    # later doesn't require a migration - validated at the Pydantic/schema layer.
    role: Mapped[str] = mapped_column(String, nullable=False)
    discord_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    dnd_beyond_character_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Cumulative seconds across all past logged-in sessions - checkpointed at
    # logout (see app/routers/auth.py), so the currently-open session's time
    # isn't included until it ends. Powers the Home dashboard's "time in
    # Lorekeeper" stat (project risk: no fabricated placeholder stats).
    total_seconds_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Campaign(Base):
    """A campaign is the top-level organizing entity for sessions - a GM
    running more than one group (or the same group across a game that ended
    and a new one that started) keeps their session logs separate this way.
    Deliberately minimal (see app/routers/campaigns.py): only a name is
    required, and it's editable later - there's no reason to force more
    setup than that up front.
    """

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    sessions: Mapped[list["SessionLog"]] = relationship(back_populates="campaign")


class SessionLog(Base):
    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    full_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    gm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{"category": "damage"|"kill"|"death"|"critical"|"strange"|"other",
    #   "description": str}, ...] - LLM-extracted from the transcript (see
    # app/ai/pipeline.py), grounded against real logged rolls
    # (RollLogEntry) that fall within recording_started_at/recording_ended_at
    # when both are set. Never fabricated placeholder content - empty if
    # extraction produced nothing or wasn't attempted.
    highlights: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Stamped by app/bot/controller.py's start_recording/stop_recording -
    # the real wall-clock window this session's recording covered, used to
    # scope which RollLogEntry rows (app/models.py) belong to this specific
    # session rather than the whole campaign's roll history. Both remain
    # None for a session whose recording predates this field, or one
    # created without ever actually recording (e.g. a manually-added log).
    recording_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recording_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Tracks the async transcription/summarization job (app.ai.pipeline).
    # "pending" (no recording processed yet) -> "processing" -> "complete" | "error".
    processing_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="sessions")
    notes: Mapped[list["Note"]] = relationship(back_populates="session", cascade="all, delete-orphan")

    @property
    def campaign_name(self) -> str:
        """Convenience read-through to campaign.name - lets
        SessionLogPublic (see app/schemas.py) keep serving a plain
        campaign_name string with no changes needed at every call site that
        already reads it, even though it is no longer a real column.
        """
        return self.campaign.name


class Note(Base):
    """
    Note visibility model - Model B ("secret note visible to one player"),
    chosen per project spec Section 4:

      - is_private_gm=False:
            Visible to everyone (GM and all players). target_player_id, if
            set, is purely informational (tags who the note is about) and has
            no effect on visibility.
      - is_private_gm=True, target_player_id=None:
            GM-only. Hidden from all players.
      - is_private_gm=True, target_player_id=<X>:
            A GM secret targeted at exactly one player. Visible to the GM and
            to player X only; hidden from every other player.

    This logic must be enforced in exactly one place - see
    app.routers.notes.get_visible_notes - rather than re-implemented at each
    call site, to avoid the two rules drifting apart.
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("session_logs.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_private_gm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_player_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    session: Mapped["SessionLog"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])
    target_player: Mapped["User | None"] = relationship(foreign_keys=[target_player_id])


class Character(Base):
    """One character per user, populated by *either* manual entry or D&D
    Beyond sync (see app/dndbeyond/sync.py) - both paths write the same
    columns so the rest of the app (character sheet, party overview) never
    needs to care which source a given character came from. Deliberately
    lean, not a full reimplementation of D&D Beyond's data model: ability
    modifiers are derived from ability_scores at read time (see
    app/routers/characters.py) rather than stored, so there's exactly one
    source of truth for them.
    """

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    # "manual" (player-entered) or "dndbeyond" (last written by a sync) - see
    # app/routers/characters.py:update_my_character for why a linked
    # character can't also be hand-edited (sync would just overwrite it).
    source: Mapped[str] = mapped_column(String, nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    race: Mapped[str] = mapped_column(String, nullable=False, default="")
    classes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    proficiency_bonus: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    ability_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    hp_current: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    hp_temp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    armor_class: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    armor_class_is_estimate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    passive_perception: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    passive_perception_is_estimate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    currencies: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # [{"name": str, "quantity": int, "equipped": bool}, ...]
    inventory: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # {"1": {"current": int, "max": int}, ..., "9": {...}} - only levels the
    # character actually has slots at need an entry. Freeform, not a full
    # SRD spell list/slot-progression table (kept lean, per project scope).
    spell_slots: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # [{"name": str, "level": int, "description": str}, ...] - level 0 = cantrip.
    known_spells: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()


class SoundClip(Base):
    """A GM soundboard clip, played into the Discord voice channel via the
    bot (see app.bot.controller.play_clip). One shared library, not scoped
    to a session/campaign - matches "GM's personal soundboard" rather than
    per-session sound cues, which is out of scope unless asked for.
    """

    __tablename__ = "sound_clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # Filename on disk under AUDIO_STORAGE_DIR/soundboard/ - a generated,
    # collision-proof name, not the user's original filename (which is only
    # used to sniff the extension at upload time).
    filename: Mapped[str] = mapped_column(String, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Encounter(Base):
    """A GM-run combat, scoped to the active campaign. At most one open
    (ended_at is None) encounter per campaign at a time - see
    app/routers/encounters.py, which enforces that rather than this model.
    Turn order is derived by sorting combatants by initiative descending
    (highest first, 5e convention) rather than stored as its own ordered
    list, so reordering never needs a data migration of its own -
    turn_index is just a position into that sorted view.
    """

    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, default="Encounter")
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    combatants: Mapped[list["Combatant"]] = relationship(back_populates="encounter", cascade="all, delete-orphan")


class Combatant(Base):
    """One participant in an Encounter - either a monster/NPC the GM typed
    in ad hoc (user_id is None) or a player's own character (user_id set).
    For a player-linked combatant, applying damage/healing here also writes
    through to that Character's hp_current (see
    app/routers/encounters.py:update_combatant) - the same HP everywhere,
    rather than a second copy that can drift from the character sheet.
    """

    __tablename__ = "combatants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    hp_current: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    armor_class: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    initiative: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    encounter: Mapped["Encounter"] = relationship(back_populates="combatants")


class RollLogEntry(Base):
    """One dice roll, broadcast to the whole table - see
    app/routers/rolls.py. Polled (GET /rolls?since_id=), the same pattern as
    presence (app/routers/users.py) rather than a websocket, consistent with
    the rest of this app's no-websocket-yet architecture. username is a
    snapshot at roll time (not a live join to User) so the log still reads
    correctly if the account is later renamed or removed.
    """

    __tablename__ = "roll_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
