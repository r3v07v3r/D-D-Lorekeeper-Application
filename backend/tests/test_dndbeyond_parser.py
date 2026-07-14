"""Tests for app.dndbeyond.parser, using synthetic data shaped like the real
character-service response (field names verified against a live public
character - see module docstring in parser.py).
"""
from app.dndbeyond.parser import parse_character

STAT_IDS = [1, 2, 3, 4, 5, 6]


def _base_character(**overrides) -> dict:
    data = {
        "name": "Test Character",
        "race": {"fullName": "Human"},
        "classes": [{"level": 5, "definition": {"name": "Fighter"}}],
        "stats": [{"id": i, "value": 10} for i in STAT_IDS],
        "bonusStats": [{"id": i, "value": None} for i in STAT_IDS],
        "overrideStats": [{"id": i, "value": None} for i in STAT_IDS],
        "baseHitPoints": 40,
        "bonusHitPoints": None,
        "removedHitPoints": 10,
        "overrideHitPoints": None,
        "temporaryHitPoints": 0,
        "inventory": [],
        "modifiers": {"race": [], "class": [], "background": [], "item": [], "feat": [], "condition": []},
        "currencies": {"cp": 0, "sp": 0, "gp": 0, "ep": 0, "pp": 0},
    }
    data.update(overrides)
    return data


def test_hp_calculation_uses_base_bonus_removed():
    result = parse_character("1", _base_character(bonusHitPoints=5, removedHitPoints=12))
    assert result.hp_max == 45
    assert result.hp_current == 33


def test_hp_calculation_respects_override_max():
    result = parse_character("1", _base_character(overrideHitPoints=99, removedHitPoints=1))
    assert result.hp_max == 99
    assert result.hp_current == 98


def test_light_armor_gets_full_dex_bonus():
    stats = [{"id": i, "value": 10} for i in STAT_IDS]
    stats[1] = {"id": 2, "value": 18}  # DEX 18 -> +4
    data = _base_character(
        stats=stats,
        inventory=[
            {"equipped": True, "definition": {"filterType": "Armor", "armorClass": 11, "armorTypeId": 1, "name": "Leather"}},
        ],
    )
    result = parse_character("1", data)
    assert result.ability_modifiers["DEX"] == 4
    assert result.armor_class == 15  # 11 + 4


def test_heavy_armor_ignores_dex_bonus():
    stats = [{"id": i, "value": 10} for i in STAT_IDS]
    stats[1] = {"id": 2, "value": 18}
    data = _base_character(
        stats=stats,
        inventory=[
            {"equipped": True, "definition": {"filterType": "Armor", "armorClass": 18, "armorTypeId": 3, "name": "Plate"}},
        ],
    )
    result = parse_character("1", data)
    assert result.armor_class == 18  # no Dex


def test_medium_armor_caps_dex_bonus_at_two():
    stats = [{"id": i, "value": 10} for i in STAT_IDS]
    stats[1] = {"id": 2, "value": 20}  # +5, should cap at +2
    data = _base_character(
        stats=stats,
        inventory=[
            {"equipped": True, "definition": {"filterType": "Armor", "armorClass": 13, "armorTypeId": 2, "name": "Half Plate"}},
        ],
    )
    result = parse_character("1", data)
    assert result.armor_class == 15  # 13 + 2


def test_equipped_shield_adds_flat_bonus():
    data = _base_character(
        inventory=[
            {"equipped": True, "definition": {"filterType": "Armor", "armorClass": 11, "armorTypeId": 1, "name": "Leather"}},
            {"equipped": True, "definition": {"filterType": "Shield", "armorClass": 2, "name": "Shield"}},
        ],
    )
    result = parse_character("1", data)
    assert result.armor_class == 13  # 11 + 0 (dex mod 0) + 2 shield


def test_unequipped_shield_does_not_count():
    data = _base_character(
        inventory=[
            {"equipped": False, "definition": {"filterType": "Shield", "armorClass": 2, "name": "Shield"}},
        ],
    )
    result = parse_character("1", data)
    assert result.armor_class == 10  # unarmored, dex mod 0


def test_passive_perception_with_proficiency():
    data = _base_character(
        modifiers={
            "race": [], "class": [], "item": [], "feat": [], "condition": [],
            "background": [{"type": "proficiency", "subType": "perception"}],
        },
    )
    # level 5 -> proficiency bonus 3; WIS mod 0 -> 10 + 0 + 3
    result = parse_character("1", data)
    assert result.passive_perception == 13


def test_passive_perception_with_expertise_doubles_bonus():
    data = _base_character(
        modifiers={
            "race": [], "class": [], "item": [], "feat": [], "condition": [],
            "background": [{"type": "expertise", "subType": "perception"}],
        },
    )
    result = parse_character("1", data)
    assert result.passive_perception == 16  # 10 + 0 + (3 * 2)


def test_passive_perception_without_proficiency():
    result = parse_character("1", _base_character())
    assert result.passive_perception == 10  # 10 + 0 + 0
