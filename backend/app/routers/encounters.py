"""GM combat tracking: encounters and their combatants, scoped to the
active campaign (see app/runtime_config.py). Any authenticated user can
view the current encounter (so players can see initiative/HP at the
table); only the GM can create/modify combatants or advance turns.

Turn order is derived by sorting combatants by initiative descending (5e
convention: highest first) rather than stored as its own list - turn_index
is a position into that sorted view. Adding/removing a combatant mid-fight
can shift what turn_index points at; the GM is expected to eyeball the
displayed order same as at a real table, not a limitation worth solving
with more machinery for a v1.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, require_gm
from app.database import get_db
from app.models import Character, Combatant, Encounter
from app.runtime_config import RuntimeConfigStore, get_runtime_config

router = APIRouter(prefix="/encounters", tags=["encounters"])


class CombatantCreate(BaseModel):
    name: str | None = None  # required unless user_id is given (defaults to that character's name)
    user_id: int | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    armor_class: int | None = None
    initiative: int = 0


class CombatantUpdate(BaseModel):
    name: str | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    armor_class: int | None = None
    initiative: int | None = None


class CombatantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    name: str
    hp_current: int
    hp_max: int
    armor_class: int
    initiative: int


class EncounterPublic(BaseModel):
    id: int
    campaign_id: int
    name: str
    round: int
    turn_index: int
    combatants: list[CombatantPublic]


def _to_public(encounter: Encounter) -> EncounterPublic:
    ordered = sorted(encounter.combatants, key=lambda c: c.initiative, reverse=True)
    return EncounterPublic(
        id=encounter.id,
        campaign_id=encounter.campaign_id,
        name=encounter.name,
        round=encounter.round,
        turn_index=encounter.turn_index,
        combatants=[CombatantPublic.model_validate(c) for c in ordered],
    )


def _active_campaign_id(runtime_config: RuntimeConfigStore) -> int:
    if not runtime_config.active_campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active campaign selected")
    return runtime_config.active_campaign_id


def _open_encounter(db: Session, campaign_id: int) -> Encounter | None:
    return (
        db.query(Encounter)
        .filter(Encounter.campaign_id == campaign_id, Encounter.ended_at.is_(None))
        .one_or_none()
    )


def _get_open_encounter_or_404(db: Session, encounter_id: int) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None or encounter.ended_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such active encounter")
    return encounter


@router.get("/active", response_model=EncounterPublic | None)
def get_active_encounter(
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(get_current_user),
) -> EncounterPublic | None:
    campaign_id = _active_campaign_id(runtime_config)
    encounter = _open_encounter(db, campaign_id)
    return _to_public(encounter) if encounter is not None else None


@router.post("", response_model=EncounterPublic, status_code=status.HTTP_201_CREATED)
def start_encounter(
    db: Session = Depends(get_db),
    runtime_config: RuntimeConfigStore = Depends(get_runtime_config),
    _current: SessionRecord = Depends(require_gm),
) -> EncounterPublic:
    campaign_id = _active_campaign_id(runtime_config)
    if _open_encounter(db, campaign_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An encounter is already in progress - end it before starting a new one",
        )
    encounter = Encounter(campaign_id=campaign_id)
    db.add(encounter)
    db.commit()
    db.refresh(encounter)
    return _to_public(encounter)


@router.post("/{encounter_id}/combatants", response_model=EncounterPublic, status_code=status.HTTP_201_CREATED)
def add_combatant(
    encounter_id: int,
    payload: CombatantCreate,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> EncounterPublic:
    encounter = _get_open_encounter_or_404(db, encounter_id)

    name = payload.name
    hp_current, hp_max, armor_class = payload.hp_current, payload.hp_max, payload.armor_class
    if payload.user_id is not None:
        character = db.query(Character).filter(Character.user_id == payload.user_id).one_or_none()
        if character is not None:
            name = name or character.name
            hp_current = hp_current if hp_current is not None else character.hp_current
            hp_max = hp_max if hp_max is not None else character.hp_max
            armor_class = armor_class if armor_class is not None else character.armor_class

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A name is required (that player has no character to default it from)",
        )

    db.add(
        Combatant(
            encounter_id=encounter.id,
            user_id=payload.user_id,
            name=name,
            hp_current=hp_current if hp_current is not None else 10,
            hp_max=hp_max if hp_max is not None else 10,
            armor_class=armor_class if armor_class is not None else 10,
            initiative=payload.initiative,
        )
    )
    db.commit()
    db.refresh(encounter)
    return _to_public(encounter)


@router.patch("/{encounter_id}/combatants/{combatant_id}", response_model=EncounterPublic)
def update_combatant(
    encounter_id: int,
    combatant_id: int,
    payload: CombatantUpdate,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> EncounterPublic:
    encounter = _get_open_encounter_or_404(db, encounter_id)
    combatant = db.get(Combatant, combatant_id)
    if combatant is None or combatant.encounter_id != encounter_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such combatant")

    if payload.name is not None:
        combatant.name = payload.name
    if payload.armor_class is not None:
        combatant.armor_class = payload.armor_class
    if payload.initiative is not None:
        combatant.initiative = payload.initiative
    if payload.hp_max is not None:
        combatant.hp_max = payload.hp_max
    if payload.hp_current is not None:
        combatant.hp_current = max(0, min(payload.hp_current, combatant.hp_max))
        # Player-linked combatant: this *is* their character's HP, not a
        # separate copy - write through so the character sheet (and the
        # GM's Party Overview) reflect damage taken in combat immediately.
        if combatant.user_id is not None:
            character = db.query(Character).filter(Character.user_id == combatant.user_id).one_or_none()
            if character is not None:
                character.hp_current = max(0, min(combatant.hp_current, character.hp_max))

    db.commit()
    db.refresh(encounter)
    return _to_public(encounter)


@router.delete("/{encounter_id}/combatants/{combatant_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_combatant(
    encounter_id: int,
    combatant_id: int,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    _get_open_encounter_or_404(db, encounter_id)
    combatant = db.get(Combatant, combatant_id)
    if combatant is None or combatant.encounter_id != encounter_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such combatant")
    db.delete(combatant)
    db.commit()


@router.post("/{encounter_id}/next-turn", response_model=EncounterPublic)
def next_turn(
    encounter_id: int,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> EncounterPublic:
    encounter = _get_open_encounter_or_404(db, encounter_id)
    count = len(encounter.combatants)
    if count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add at least one combatant first")

    next_index = encounter.turn_index + 1
    if next_index >= count:
        next_index = 0
        encounter.round += 1
    encounter.turn_index = next_index
    db.commit()
    db.refresh(encounter)
    return _to_public(encounter)


@router.post("/{encounter_id}/end", status_code=status.HTTP_204_NO_CONTENT)
def end_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(require_gm),
) -> None:
    encounter = _get_open_encounter_or_404(db, encounter_id)
    encounter.ended_at = datetime.utcnow()
    db.commit()
