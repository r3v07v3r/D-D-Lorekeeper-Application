"""GM soundboard: upload/manage short audio clips and play them either into
the Discord voice channel via the bot (see app.bot.controller.play_clip/
stop_playback), or locally through this computer's own speakers so a GM
without a bot configured yet (or who just prefers it) can still cue sound
effects - the clip plays out loud and rides along on whatever mic/Discord
call the GM already has open, the same way a GM playing music from a phone
near an open mic works today, just automated. One shared clip library,
GM-only throughout - players have no reason to trigger or manage these.
"""
import base64

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import SessionRecord, require_gm
from app.bot import controller
from app.database import get_db
from app.models import SoundClip
from app.routers.bot_control import get_bot_state
from app.runtime_config import RuntimeConfigStore, get_runtime_config
from app.schemas import SoundClipAudio, SoundClipPublic, SoundClipUpdate, SoundClipUpload
from app.soundboard import MIME_TYPES, SoundClipError, decode_clip, delete_clip_file, save_clip_file, validate_extension
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


@router.get("/{clip_id}/audio", response_model=SoundClipAudio)
def get_clip_audio(
    clip_id: int,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> SoundClipAudio:
    """Raw clip bytes for local (non-bot) playback in the renderer - base64
    in a JSON body rather than a binary response, since the packaged app's
    requests are proxied through Electron's main process over IPC (see
    SoundClipUpload's docstring), which only carries string bodies.
    """
    clip = db.get(SoundClip, clip_id)
    if clip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such clip")
    file_path = _storage_dir(runtime_config) / clip.filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip file missing on disk")
    extension = file_path.suffix.lower()
    return SoundClipAudio(
        content_base64=base64.b64encode(file_path.read_bytes()).decode("ascii"),
        mime_type=MIME_TYPES.get(extension, "application/octet-stream"),
    )


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
