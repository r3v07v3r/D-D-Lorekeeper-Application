"""Serves cached D&D Beyond character data (see app.dndbeyond.sync).

Per project spec Section 5: players see only their own character
(GET /characters/me, scoped to the session's own user_id - never a
client-supplied id); the GM sees the whole party
(GET /characters/party, GM-only).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, require_gm
from app.database import get_db
from app.dndbeyond.parser import ParsedCharacter
from app.dndbeyond.sync import CharacterSyncState
from app.models import User

router = APIRouter(prefix="/characters", tags=["characters"])


class InventoryItemPublic(BaseModel):
    name: str
    quantity: int
    equipped: bool


class CharacterPublic(BaseModel):
    character_id: str
    name: str
    race: str
    classes: list[str]
    level: int
    proficiency_bonus: int
    ability_scores: dict[str, int]
    ability_modifiers: dict[str, int]
    hp_current: int
    hp_max: int
    hp_temp: int
    armor_class: int
    armor_class_is_estimate: bool
    passive_perception: int
    passive_perception_is_estimate: bool
    currencies: dict[str, int]
    inventory: list[InventoryItemPublic]


class PartyMemberPublic(BaseModel):
    user_id: int
    username: str
    character: CharacterPublic | None = None
    sync_error: str | None = None


def _to_public(parsed: ParsedCharacter) -> CharacterPublic:
    return CharacterPublic(
        character_id=parsed.character_id,
        name=parsed.name,
        race=parsed.race,
        classes=parsed.classes,
        level=parsed.level,
        proficiency_bonus=parsed.proficiency_bonus,
        ability_scores=parsed.ability_scores,
        ability_modifiers=parsed.ability_modifiers,
        hp_current=parsed.hp_current,
        hp_max=parsed.hp_max,
        hp_temp=parsed.hp_temp,
        armor_class=parsed.armor_class,
        armor_class_is_estimate=parsed.armor_class_is_estimate,
        passive_perception=parsed.passive_perception,
        passive_perception_is_estimate=parsed.passive_perception_is_estimate,
        currencies=parsed.currencies,
        inventory=[InventoryItemPublic(**vars(item)) for item in parsed.inventory],
    )


def get_sync_state(request: Request) -> CharacterSyncState:
    return request.app.state.dndbeyond_sync


@router.get("/me", response_model=CharacterPublic)
def get_my_character(
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
    sync_state: CharacterSyncState = Depends(get_sync_state),
) -> CharacterPublic:
    user = db.get(User, current.user_id)
    if user is None or not user.dnd_beyond_character_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No D&D Beyond character linked to this profile")

    parsed = sync_state.characters.get(current.user_id)
    if parsed is None:
        error = sync_state.errors.get(current.user_id, "Not synced yet")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Character not available: {error}")
    return _to_public(parsed)


@router.get("/party", response_model=list[PartyMemberPublic])
def get_party_overview(
    db: Session = Depends(get_db),
    sync_state: CharacterSyncState = Depends(get_sync_state),
    _current: SessionRecord = Depends(require_gm),
) -> list[PartyMemberPublic]:
    players = db.query(User).filter(User.role == "player").order_by(User.username).all()
    overview = []
    for player in players:
        parsed = sync_state.characters.get(player.id)
        overview.append(
            PartyMemberPublic(
                user_id=player.id,
                username=player.username,
                character=_to_public(parsed) if parsed is not None else None,
                sync_error=sync_state.errors.get(player.id) if parsed is None else None,
            )
        )
    return overview


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    db: Session = Depends(get_db),
    sync_state: CharacterSyncState = Depends(get_sync_state),
    _current: SessionRecord = Depends(require_gm),
) -> dict[str, str]:
    await sync_state.sync_once(db)
    return {"status": "synced"}
