"""Character sheets: one Character row per user (see app/models.py),
populated by either manual entry (this router) or D&D Beyond sync (see
app/dndbeyond/sync.py) - both paths write the same columns, so the rest of
the app never needs to care which source a character came from.

Per project spec Section 5: players see only their own character
(GET /characters/me, scoped to the session's own user_id - never a
client-supplied id); the GM sees the whole party (GET /characters/party,
GM-only).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, require_gm
from app.database import get_db
from app.dndbeyond.sync import CharacterSyncState
from app.models import Character, User

router = APIRouter(prefix="/characters", tags=["characters"])

_ABILITY_NAMES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


class InventoryItemPublic(BaseModel):
    name: str
    quantity: int = 1
    equipped: bool = False


class SpellSlotInfo(BaseModel):
    current: int
    max: int


class KnownSpell(BaseModel):
    name: str
    level: int = Field(ge=0, le=9)  # 0 = cantrip
    description: str = ""


class CharacterPublic(BaseModel):
    source: str  # "manual" | "dndbeyond"
    character_id: str  # kept for frontend compatibility - the User.id as a string, not a D&D Beyond id
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
    spell_slots: dict[str, SpellSlotInfo]
    known_spells: list[KnownSpell]


class CharacterInput(BaseModel):
    """Manual character create/edit. Ability modifiers and the AC/passive-
    perception "estimate" flags aren't settable here - a manually-entered
    character's AC/passive perception are numbers the player typed in
    directly, not an estimate, and modifiers are always derived from
    ability_scores (see _to_public below) so there's one source of truth.
    """

    name: str
    race: str = ""
    classes: list[str] = []
    level: int = Field(default=1, ge=1)
    proficiency_bonus: int = Field(default=2, ge=2)
    ability_scores: dict[str, int]
    hp_current: int
    hp_max: int
    hp_temp: int = 0
    armor_class: int
    passive_perception: int
    currencies: dict[str, int] = {}
    inventory: list[InventoryItemPublic] = []
    spell_slots: dict[str, SpellSlotInfo] = {}
    known_spells: list[KnownSpell] = []


class PartyMemberPublic(BaseModel):
    user_id: int
    username: str
    character: CharacterPublic | None = None
    sync_error: str | None = None


def _ability_modifier(score: int) -> int:
    return (score - 10) // 2


def _to_public(character: Character) -> CharacterPublic:
    ability_scores = character.ability_scores or {}
    ability_modifiers = {name: _ability_modifier(ability_scores.get(name, 10)) for name in _ABILITY_NAMES}
    return CharacterPublic(
        source=character.source,
        character_id=str(character.user_id),
        name=character.name,
        race=character.race,
        classes=character.classes,
        level=character.level,
        proficiency_bonus=character.proficiency_bonus,
        ability_scores=ability_scores,
        ability_modifiers=ability_modifiers,
        hp_current=character.hp_current,
        hp_max=character.hp_max,
        hp_temp=character.hp_temp,
        armor_class=character.armor_class,
        armor_class_is_estimate=character.armor_class_is_estimate,
        passive_perception=character.passive_perception,
        passive_perception_is_estimate=character.passive_perception_is_estimate,
        currencies=character.currencies or {},
        inventory=[InventoryItemPublic(**item) for item in (character.inventory or [])],
        spell_slots={level: SpellSlotInfo(**slot) for level, slot in (character.spell_slots or {}).items()},
        known_spells=[KnownSpell(**spell) for spell in (character.known_spells or [])],
    )


def get_sync_state(request: Request) -> CharacterSyncState:
    return request.app.state.dndbeyond_sync


@router.get("/me", response_model=CharacterPublic)
def get_my_character(
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> CharacterPublic:
    character = db.query(Character).filter(Character.user_id == current.user_id).one_or_none()
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No character yet - create one manually, or link a D&D Beyond character in Settings",
        )
    return _to_public(character)


@router.put("/me", response_model=CharacterPublic)
def update_my_character(
    payload: CharacterInput,
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> CharacterPublic:
    user = db.get(User, current.user_id)
    if user is not None and user.dnd_beyond_character_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This character is linked to D&D Beyond - unlink it in Settings before editing it manually, "
            "since the next sync would just overwrite your changes.",
        )

    character = db.query(Character).filter(Character.user_id == current.user_id).one_or_none()
    if character is None:
        character = Character(user_id=current.user_id, source="manual")
        db.add(character)
    character.source = "manual"
    character.name = payload.name
    character.race = payload.race
    character.classes = payload.classes
    character.level = payload.level
    character.proficiency_bonus = payload.proficiency_bonus
    character.ability_scores = payload.ability_scores
    character.hp_current = payload.hp_current
    character.hp_max = payload.hp_max
    character.hp_temp = payload.hp_temp
    character.armor_class = payload.armor_class
    character.armor_class_is_estimate = False
    character.passive_perception = payload.passive_perception
    character.passive_perception_is_estimate = False
    character.currencies = payload.currencies
    character.inventory = [item.model_dump() for item in payload.inventory]
    character.spell_slots = {level: slot.model_dump() for level, slot in payload.spell_slots.items()}
    character.known_spells = [spell.model_dump() for spell in payload.known_spells]
    db.commit()
    db.refresh(character)
    return _to_public(character)


@router.post("/me/rest", response_model=CharacterPublic)
def long_rest(
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> CharacterPublic:
    """A long rest (5e RAW): full HP restored, temp HP cleared, all spell
    slots restored to max. Short rest isn't modeled - 5e's short rest
    recovery (spending hit dice, Warlock slots) isn't a simple full-reset
    like this, and faking it would be actively wrong rather than just
    incomplete.
    """
    character = db.query(Character).filter(Character.user_id == current.user_id).one_or_none()
    if character is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No character to rest")

    character.hp_current = character.hp_max
    character.hp_temp = 0
    character.spell_slots = {
        level: {"current": slot["max"], "max": slot["max"]} for level, slot in (character.spell_slots or {}).items()
    }
    db.commit()
    db.refresh(character)
    return _to_public(character)


@router.get("/party", response_model=list[PartyMemberPublic])
def get_party_overview(
    db: Session = Depends(get_db),
    sync_state: CharacterSyncState = Depends(get_sync_state),
    _current: SessionRecord = Depends(require_gm),
) -> list[PartyMemberPublic]:
    players = db.query(User).filter(User.role == "player").order_by(User.username).all()
    characters_by_user = {c.user_id: c for c in db.query(Character).all()}
    overview = []
    for player in players:
        character = characters_by_user.get(player.id)
        overview.append(
            PartyMemberPublic(
                user_id=player.id,
                username=player.username,
                character=_to_public(character) if character is not None else None,
                sync_error=sync_state.errors.get(player.id) if character is None else None,
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
