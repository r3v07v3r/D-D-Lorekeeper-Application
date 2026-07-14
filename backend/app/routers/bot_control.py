"""GM-only endpoints for controlling the Discord bot's voice connection and
recording from the dashboard (as opposed to a Discord slash command). Every
route here is gated with require_gm - the frontend hiding these buttons for
players is not sufficient on its own (risk #1).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import SessionRecord, require_gm
from app.bot import controller
from app.config import get_settings
from app.database import get_db
from app.models import SessionLog
from app.state import BotState

router = APIRouter(prefix="/bot", tags=["bot-control"])


def get_bot_state(request: Request) -> BotState:
    return request.app.state.bot_state


class JoinRequest(BaseModel):
    discord_channel_id: int


class RecordStartRequest(BaseModel):
    session_log_id: int


class BotStatusResponse(BaseModel):
    connected: bool
    is_recording: bool
    current_session_log_id: int | None


@router.get("/status", response_model=BotStatusResponse)
def status_(
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> BotStatusResponse:
    return BotStatusResponse(
        connected=bot_state.voice_client is not None and bot_state.voice_client.is_connected(),
        is_recording=bot_state.is_recording,
        current_session_log_id=bot_state.current_session_log_id,
    )


@router.post("/join", status_code=status.HTTP_204_NO_CONTENT)
async def join(
    payload: JoinRequest,
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    if bot_state.bot is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord bot is not running")
    channel = bot_state.bot.get_channel(payload.discord_channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such Discord channel")
    try:
        await controller.join_channel(bot_state, channel)
    except controller.VoiceControlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave(
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    try:
        await controller.leave_channel(bot_state)
    except controller.VoiceControlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/record/start", status_code=status.HTTP_204_NO_CONTENT)
async def record_start(
    payload: RecordStartRequest,
    db: Session = Depends(get_db),
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    if db.get(SessionLog, payload.session_log_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such session log")
    try:
        await controller.start_recording(bot_state, payload.session_log_id, get_settings())
    except controller.VoiceControlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/record/stop", status_code=status.HTTP_204_NO_CONTENT)
async def record_stop(
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    try:
        await controller.stop_recording(bot_state)
    except controller.VoiceControlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
