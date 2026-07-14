"""SQLAlchemy models: Users, SessionLogs, Notes."""
from datetime import date as date_type

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class SessionLog(Base):
    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_name: Mapped[str] = mapped_column(String, nullable=False)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    full_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    gm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tracks the async transcription/summarization job (app.ai.pipeline).
    # "pending" (no recording processed yet) -> "processing" -> "complete" | "error".
    processing_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[list["Note"]] = relationship(back_populates="session", cascade="all, delete-orphan")


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
