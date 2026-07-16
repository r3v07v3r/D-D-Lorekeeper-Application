"""SessionLog CRUD.

Reading the full (uncensored) transcript/gm_summary is GM-only; the
player_summary field is safe for anyone authenticated to read. Creating a
session log is GM-only (only the GM runs the bot / starts a session).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.pipeline import process_session
from app.auth import SessionRecord, get_current_user, require_gm
from app.database import get_db
from app.models import SessionLog
from app.runtime_config import RuntimeConfigStore, get_runtime_config
from app.schemas import SessionLogCreate, SessionLogPublic

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _redact_for_role(log: SessionLog, role: str) -> SessionLogPublic:
    """Builds the response DTO directly rather than mutating the ORM-tracked
    `log` instance in place - mutating it could leak into a later commit on
    the same session (e.g. added by unrelated code down the line).
    """
    public = SessionLogPublic.model_validate(log)
    if role != "gm":
        public.full_transcript = None
        public.gm_summary = None
    return public


@router.get("", response_model=list[SessionLogPublic])
def list_sessions(
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    current: SessionRecord = Depends(get_current_user),
) -> list[SessionLogPublic]:
    # No active campaign yet (fresh install, or the GM hasn't picked one) -
    # nothing to show rather than an unfiltered dump across every campaign
    # that has ever existed on this install.
    if not runtime_config.active_campaign_id:
        return []
    logs = (
        db.query(SessionLog)
        .filter(SessionLog.campaign_id == runtime_config.active_campaign_id)
        .order_by(SessionLog.session_number)
        .all()
    )
    return [_redact_for_role(log, current.role) for log in logs]


@router.get("/{session_id}", response_model=SessionLogPublic)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> SessionLogPublic:
    log = db.get(SessionLog, session_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such session")
    return _redact_for_role(log, current.role)


@router.post("", response_model=SessionLogPublic, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionLogCreate,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> SessionLog:
    if not runtime_config.active_campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active campaign selected - choose or create one first",
        )
    log = SessionLog(
        campaign_id=runtime_config.active_campaign_id,
        session_number=payload.session_number,
        date=payload.date,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/{session_id}/process", status_code=status.HTTP_202_ACCEPTED)
def process(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> dict[str, str]:
    """Kicks off transcription + summarization for a recorded session.
    Runs in the background - poll GET /sessions/{id} and watch
    processing_status (pending -> processing -> complete | error).
    """
    log = db.get(SessionLog, session_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such session")
    if log.processing_status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already processing")

    if not runtime_config.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No OpenAI API key configured - add one in Settings",
        )

    log.processing_status = "processing"
    db.commit()
    background_tasks.add_task(process_session, session_id, runtime_config)
    return {"status": "processing"}
