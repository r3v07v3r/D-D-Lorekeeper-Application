"""Orchestrates transcription + summarization for one session and persists
the result onto the SessionLog row. Runs as a FastAPI BackgroundTask (see
app/routers/sessions.py) since a multi-hour session can take several minutes
to transcribe - the triggering HTTP request should not block on it.
"""
import logging

from sqlalchemy.orm import Session

from app.ai.summarization import build_llm_client, generate_gm_summary, generate_highlights, generate_player_summary
from app.ai.transcript_builder import build_session_transcript
from app.config import Settings
from app.database import SessionLocal
from app.models import RollLogEntry, SessionLog
from app.runtime_config import RuntimeConfigStore

logger = logging.getLogger(__name__)


def _build_roll_context(db: Session, log: SessionLog) -> str:
    """Formats the actual dice rolls logged during this session's real
    recording window (see app/bot/controller.py) as grounding context for
    generate_highlights - empty if the window isn't known (an older session,
    or one that was never actually recorded) or no rolls fell inside it.
    """
    if log.recording_started_at is None or log.recording_ended_at is None:
        return ""
    rolls = (
        db.query(RollLogEntry)
        .filter(
            RollLogEntry.campaign_id == log.campaign_id,
            RollLogEntry.created_at >= log.recording_started_at,
            RollLogEntry.created_at <= log.recording_ended_at,
        )
        .order_by(RollLogEntry.id)
        .all()
    )
    return "\n".join(f"{r.username}: {r.summary} = {r.total}" for r in rolls)


def process_session(session_log_id: int, settings: Settings | RuntimeConfigStore) -> None:
    """Synchronous entrypoint suitable for BackgroundTasks/a thread - opens
    its own DB session since it may run after the request's session has
    already closed.
    """
    db: Session = SessionLocal()
    try:
        log = db.get(SessionLog, session_log_id)
        if log is None:
            logger.error("process_session: no SessionLog with id %s", session_log_id)
            return

        log.processing_status = "processing"
        log.processing_error = None
        db.commit()

        session_dir = settings.audio_storage_dir / f"session_{session_log_id}"
        if not session_dir.exists():
            raise FileNotFoundError(f"No recordings found for session {session_log_id} at {session_dir}")

        transcript = build_session_transcript(session_dir, db, settings)
        if not transcript.strip():
            raise ValueError("Transcription produced no text - check that recording chunks exist and are audible")

        llm_client = build_llm_client(settings)
        gm_summary = generate_gm_summary(transcript, llm_client, settings.summarization_model)
        player_summary = generate_player_summary(transcript, llm_client, settings.summarization_model)

        # Non-fatal: a session's transcript/summaries are still worth having
        # even if highlight extraction fails or the model returns something
        # unparseable - see generate_highlights' own empty-list-on-failure
        # behavior, this just adds a second layer for anything that raises.
        highlights = []
        try:
            roll_context = _build_roll_context(db, log)
            highlights = generate_highlights(transcript, roll_context, llm_client, settings.summarization_model)
        except Exception:
            logger.warning("Could not extract highlights for session %s", session_log_id, exc_info=True)

        log.full_transcript = transcript
        log.gm_summary = gm_summary
        log.player_summary = player_summary
        log.highlights = highlights
        log.processing_status = "complete"
        db.commit()
    except Exception as exc:
        logger.exception("Failed to process session %s", session_log_id)
        log = db.get(SessionLog, session_log_id)
        if log is not None:
            log.processing_status = "error"
            log.processing_error = str(exc)
            db.commit()
    finally:
        db.close()
