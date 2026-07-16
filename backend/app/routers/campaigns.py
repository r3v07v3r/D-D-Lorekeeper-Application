"""Campaigns: the top-level entity sessions belong to (see app/models.py's
Campaign docstring for why - a GM running more than one group, or starting a
new campaign after an old one wraps up, wants those sessions kept separate).

The "active" campaign is stored in RuntimeConfigStore rather than session-
scoped: it's what new sessions get created under and what GET /sessions
returns, and it needs to be the same answer for the GM's own app and for
any player connecting to it - there is deliberately no per-player campaign
picker, only the GM chooses which one is currently being played.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, require_gm
from app.database import get_db
from app.models import Campaign
from app.runtime_config import RuntimeConfigStore, get_runtime_config
from app.schemas import CampaignCreate, CampaignPublic, SetActiveCampaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignPublic])
def list_campaigns(
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(get_current_user),
) -> list[Campaign]:
    return db.query(Campaign).order_by(Campaign.created_at).all()


@router.post("", response_model=CampaignPublic, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> Campaign:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign name cannot be empty")
    campaign = Campaign(name=name)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignPublic)
def rename_campaign(
    campaign_id: int,
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such campaign")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign name cannot be empty")
    campaign.name = name
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/active", response_model=CampaignPublic | None)
def get_active_campaign(
    db: Session = Depends(get_db),
    config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(get_current_user),
) -> Campaign | None:
    if not config.active_campaign_id:
        return None
    return db.get(Campaign, config.active_campaign_id)


@router.put("/active", response_model=CampaignPublic)
def set_active_campaign(
    payload: SetActiveCampaign,
    db: Session = Depends(get_db),
    config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> Campaign:
    campaign = db.get(Campaign, payload.campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such campaign")
    config.update(active_campaign_id=campaign.id)
    return campaign
