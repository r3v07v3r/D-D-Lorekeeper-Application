"""Shared dice-roll log for the active campaign - broadcasts each roll
(see frontend/src/utils/diceEngine.ts) to everyone at the table via polling
(GET /rolls?since_id=), the same pattern as presence (app/routers/users.py)
rather than a websocket, consistent with the rest of this app's
no-websocket-yet architecture.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user
from app.database import get_db
from app.models import RollLogEntry
from app.runtime_config import RuntimeConfigStore, get_runtime_config

router = APIRouter(prefix="/rolls", tags=["rolls"])


class RollCreate(BaseModel):
    summary: str
    total: int


class RollPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    summary: str
    total: int
    created_at: datetime


@router.get("", response_model=list[RollPublic])
def list_rolls(
    since_id: int = 0,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(get_current_user),
) -> list[RollLogEntry]:
    if not runtime_config.active_campaign_id:
        return []
    return (
        db.query(RollLogEntry)
        .filter(RollLogEntry.campaign_id == runtime_config.active_campaign_id, RollLogEntry.id > since_id)
        .order_by(RollLogEntry.id)
        .limit(100)
        .all()
    )


@router.post("", response_model=RollPublic, status_code=status.HTTP_201_CREATED)
def create_roll(
    payload: RollCreate,
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    current: SessionRecord = Depends(get_current_user),
) -> RollLogEntry:
    if not runtime_config.active_campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active campaign selected")
    entry = RollLogEntry(
        campaign_id=runtime_config.active_campaign_id,
        user_id=current.user_id,
        username=current.username,
        summary=payload.summary,
        total=payload.total,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
