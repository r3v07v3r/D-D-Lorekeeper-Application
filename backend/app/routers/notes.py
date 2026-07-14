"""Session notes, with server-enforced Model B visibility (see app.models.Note
docstring for the full rule). Viewer identity/role always come from the
resolved session (get_current_user) - never from a query param or body field
supplied by the client. This is the fix for the first-draft vulnerability
where GET /sessions/{id}/notes accepted user_discord_id/include_private
directly from the client.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user
from app.database import get_db
from app.models import Note, SessionLog
from app.schemas import NoteCreate, NotePublic

router = APIRouter(prefix="/sessions", tags=["notes"])


def get_visible_notes(db: Session, session_id: int, viewer: SessionRecord) -> list[Note]:
    """Single source of truth for Note visibility (Model B). Every route that
    returns notes must go through this function rather than re-deriving the
    filter, so the GM/player rules can't drift apart across endpoints.
    """
    query = db.query(Note).filter(Note.session_id == session_id)

    if viewer.role == "gm":
        return query.order_by(Note.id).all()

    # Player: visible if the note isn't private, OR it's a secret targeted at
    # exactly this player.
    query = query.filter(
        or_(
            Note.is_private_gm.is_(False),
            and_(Note.is_private_gm.is_(True), Note.target_player_id == viewer.user_id),
        )
    )
    return query.order_by(Note.id).all()


@router.get("/{session_id}/notes", response_model=list[NotePublic])
def list_notes(
    session_id: int,
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> list[Note]:
    if db.get(SessionLog, session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such session")
    return get_visible_notes(db, session_id, current)


@router.post("/{session_id}/notes", response_model=NotePublic, status_code=status.HTTP_201_CREATED)
def create_note(
    session_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> Note:
    if db.get(SessionLog, session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such session")

    # Only the GM can author a secret note. A player attempting to set either
    # flag is rejected outright rather than silently downgraded, so the
    # mistake is visible instead of quietly producing a public note.
    if (payload.is_private_gm or payload.target_player_id is not None) and current.role != "gm":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can create a private or player-targeted note",
        )

    note = Note(
        session_id=session_id,
        author_id=current.user_id,  # server-derived, never client-supplied
        content=payload.content,
        is_private_gm=payload.is_private_gm,
        target_player_id=payload.target_player_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
