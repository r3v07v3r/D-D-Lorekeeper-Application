"""Parses the raw D&D Beyond character-service JSON (see client.py) into the
subset of fields this app's dashboard actually needs: HP, ability scores,
armor class, passive perception, and inventory/currency.

Schema notes (verified against a live public character during development -
this API is unofficial and undocumented, so field names could change):
  - Ability scores: `stats` is a fixed-order array of 6 {id, value} entries,
    id 1-6 = STR, DEX, CON, INT, WIS, CHA. `bonusStats`/`overrideStats` are
    same-shaped arrays of nullable overlays applied on top.
  - HP: current = baseHitPoints + (bonusHitPoints or 0) - (removedHitPoints or 0);
    max = overrideHitPoints if set, else baseHitPoints + (bonusHitPoints or 0).
  - Proficiencies (including skill proficiency, used for passive perception):
    scattered across `modifiers.{race,class,background,item,feat,condition}`,
    each entry has a `type` ("proficiency" | "expertise" | "bonus" | ...) and a
    `subType` (e.g. "perception").
  - Inventory: `inventory` is a flat array; equipped armor pieces have
    `definition.filterType == "Armor"` with a base `definition.armorClass`
    and `definition.armorTypeId` (1=light, 2=medium, 3=heavy); shields have
    `definition.filterType == "Shield"` with `definition.armorClass` as a
    flat AC bonus.

IMPORTANT LIMITATION: armor_class and passive_perception below are
*best-effort estimates*, not a reimplementation of D&D Beyond's full rules
engine. They cover the common cases (standard armor, standard skill
proficiency/expertise) but will not exactly match the character sheet for
things like unarmored defense (barbarian/monk), the Observant feat, or
other situational modifiers layered on top. Surface them in the UI as
"~AC" / estimates, not as guaranteed-exact values (Phase 4 should label
these clearly rather than presenting them as authoritative).
"""
from dataclasses import dataclass, field

from app.dndbeyond.client import fetch_character_raw

_ABILITY_NAMES = {1: "STR", 2: "DEX", 3: "CON", 4: "INT", 5: "WIS", 6: "CHA"}


@dataclass
class InventoryItem:
    name: str
    quantity: int
    equipped: bool


@dataclass
class ParsedCharacter:
    character_id: str
    name: str
    race: str
    classes: list[str]  # e.g. ["Rogue 5"]
    level: int
    proficiency_bonus: int
    ability_scores: dict[str, int]  # e.g. {"STR": 10, "DEX": 18, ...}
    ability_modifiers: dict[str, int]
    hp_current: int
    hp_max: int
    hp_temp: int
    armor_class: int
    armor_class_is_estimate: bool
    passive_perception: int
    passive_perception_is_estimate: bool
    currencies: dict[str, int]
    inventory: list[InventoryItem] = field(default_factory=list)


def _ability_modifier(score: int) -> int:
    return (score - 10) // 2


def _resolve_stats(data: dict) -> dict[int, int]:
    base = {s["id"]: s["value"] for s in data["stats"]}
    bonus = {s["id"]: s["value"] for s in data["bonusStats"] if s["value"] is not None}
    override = {s["id"]: s["value"] for s in data["overrideStats"] if s["value"] is not None}
    resolved = dict(base)
    for stat_id, value in bonus.items():
        resolved[stat_id] = resolved.get(stat_id, 0) + value
    resolved.update(override)
    return resolved


def _all_modifiers(data: dict) -> list[dict]:
    modifiers = data.get("modifiers") or {}
    return [m for group in modifiers.values() for m in group]


def _has_modifier(modifiers: list[dict], mod_type: str, sub_type: str) -> bool:
    return any(m.get("type") == mod_type and m.get("subType") == sub_type for m in modifiers)


def _flat_bonus(modifiers: list[dict], sub_type: str) -> int:
    total = 0
    for m in modifiers:
        if m.get("type") == "bonus" and m.get("subType") == sub_type:
            total += m.get("value") or m.get("fixedValue") or 0
    return total


def _estimate_armor_class(data: dict, dex_modifier: int) -> int:
    equipped_armor = None
    equipped_shield_bonus = 0
    for item in data.get("inventory", []):
        if not item.get("equipped"):
            continue
        definition = item.get("definition") or {}
        if definition.get("filterType") == "Armor" and definition.get("armorClass") is not None:
            equipped_armor = definition
        elif definition.get("filterType") == "Shield" and definition.get("armorClass") is not None:
            equipped_shield_bonus += definition["armorClass"]

    if equipped_armor is None:
        base_ac = 10 + dex_modifier  # unarmored - does not account for class features like Unarmored Defense
    else:
        armor_type = equipped_armor.get("armorTypeId")
        base = equipped_armor["armorClass"]
        if armor_type == 1:  # light armor: full Dex
            base_ac = base + dex_modifier
        elif armor_type == 2:  # medium armor: Dex capped at +2
            base_ac = base + min(dex_modifier, 2)
        else:  # heavy armor: no Dex
            base_ac = base

    return base_ac + equipped_shield_bonus


def _estimate_passive_perception(data: dict, wisdom_modifier: int, proficiency_bonus: int) -> int:
    modifiers = _all_modifiers(data)
    if _has_modifier(modifiers, "expertise", "perception"):
        prof_component = proficiency_bonus * 2
    elif _has_modifier(modifiers, "proficiency", "perception") or _has_modifier(modifiers, "half-proficiency", "perception"):
        prof_component = proficiency_bonus
    else:
        prof_component = 0

    flat_bonus = _flat_bonus(modifiers, "passive-perception")
    return 10 + wisdom_modifier + prof_component + flat_bonus


def parse_character(character_id: str, data: dict) -> ParsedCharacter:
    stats = _resolve_stats(data)
    ability_scores = {_ABILITY_NAMES[i]: stats.get(i, 10) for i in range(1, 7)}
    ability_modifiers = {name: _ability_modifier(score) for name, score in ability_scores.items()}

    level = sum(c["level"] for c in data.get("classes", []))
    proficiency_bonus = 2 + max(level - 1, 0) // 4

    hp_max = data.get("overrideHitPoints") or (data["baseHitPoints"] + (data.get("bonusHitPoints") or 0))
    hp_current = hp_max - (data.get("removedHitPoints") or 0)
    hp_temp = data.get("temporaryHitPoints") or 0

    armor_class = _estimate_armor_class(data, ability_modifiers["DEX"])
    passive_perception = _estimate_passive_perception(data, ability_modifiers["WIS"], proficiency_bonus)

    inventory = [
        InventoryItem(
            name=(item.get("definition") or {}).get("name", "Unknown item"),
            quantity=item.get("quantity", 1),
            equipped=bool(item.get("equipped")),
        )
        for item in data.get("inventory", [])
    ]

    race = data.get("race", {}).get("fullName") or data.get("race", {}).get("baseName") or "Unknown"

    return ParsedCharacter(
        character_id=character_id,
        name=data.get("name", "Unnamed character"),
        race=race,
        classes=[f"{c['definition']['name']} {c['level']}" for c in data.get("classes", [])],
        level=level,
        proficiency_bonus=proficiency_bonus,
        ability_scores=ability_scores,
        ability_modifiers=ability_modifiers,
        hp_current=hp_current,
        hp_max=hp_max,
        hp_temp=hp_temp,
        armor_class=armor_class,
        armor_class_is_estimate=True,
        passive_perception=passive_perception,
        passive_perception_is_estimate=True,
        currencies=data.get("currencies", {}),
        inventory=inventory,
    )


async def fetch_and_parse_character(character_id: str) -> ParsedCharacter:
    raw = await fetch_character_raw(character_id)
    return parse_character(character_id, raw)
