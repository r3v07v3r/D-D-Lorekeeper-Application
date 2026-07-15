"""GM soundboard: upload/manage short audio clips and play them into the
Discord voice channel via the bot (see app.bot.controller.play_clip/
stop_playback). One shared clip library, GM-only throughout - players have
no reason to trigger or manage these.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import SessionRecord, require_gm
from app.bot import controller
from app.database import get_db
from app.models import SoundClip
from app.routers.bot_control import get_bot_state
from app.runtime_config import RuntimeConfigStore, get_runtime_config
from app.schemas import SoundClipPublic, SoundClipUpdate, SoundClipUpload
from app.soundboard import SoundClipError, decode_clip, delete_clip_file, save_clip_file, validate_extension
from app.state import BotState

router = APIRouter(prefix="/soundboard", tags=["soundboard"])


def _storage_dir(runtime_config: RuntimeConfigStore):
    return runtime_config.audio_storage_dir / "soundboard"


@router.get("", response_model=list[SoundClipPublic])
def list_clips(
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> list[SoundClip]:
    return db.query(SoundClip).order_by(SoundClip.name).all()


@router.post("", response_model=SoundClipPublic, status_code=status.HTTP_201_CREATED)
def upload_clip(
    payload: SoundClipUpload,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> SoundClip:
    try:
        extension = validate_extension(payload.filename)
        data = decode_clip(payload.content_base64)
        filename = save_clip_file(_storage_dir(runtime_config), extension, data)
    except SoundClipError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    clip = SoundClip(name=payload.name, filename=filename, volume=payload.volume)
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip


@router.patch("/{clip_id}", response_model=SoundClipPublic)
def update_clip(
    clip_id: int,
    payload: SoundClipUpdate,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> SoundClip:
    clip = db.get(SoundClip, clip_id)
    if clip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such clip")
    if payload.name is not None:
        clip.name = payload.name
    if payload.volume is not None:
        clip.volume = payload.volume
    db.commit()
    db.refresh(clip)
    return clip


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    clip = db.get(SoundClip, clip_id)
    if clip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such clip")
    delete_clip_file(_storage_dir(runtime_config), clip.filename)
    db.delete(clip)
    db.commit()


@router.post("/{clip_id}/play", status_code=status.HTTP_204_NO_CONTENT)
def play_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    clip = db.get(SoundClip, clip_id)
    if clip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such clip")
    file_path = _storage_dir(runtime_config) / clip.filename
    try:
        controller.play_clip(bot_state, file_path, volume=clip.volume)
    except controller.VoiceControlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/stop", status_code=status.HTTP_204_NO_CONTENT)
def stop_clip(
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    try:
        controller.stop_playback(bot_state)
    except controller.VoiceControlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
