"""Tests for GM combat tracking - Encounter/Combatant (see app/models.py and
app/routers/encounters.py): starting/ending an encounter, adding combatants
(including a player-linked one defaulting from their Character), applying
damage that writes through to the linked Character's HP, and turn/round
advancement.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Mirrors tests/test_soundboard.py's client fixture - see its docstring
    for why the database engine/settings cache need patching this way.
    """
    import app.database as database_module

    test_engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database_module, "engine", test_engine)
    monkeypatch.setattr(database_module, "SessionLocal", TestSessionLocal)
    database_module.Base.metadata.create_all(bind=test_engine)

    monkeypatch.setenv("LOREKEEPER_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("AUDIO_STORAGE_DIR", str(tmp_path / "recordings"))

    from app.config import get_settings
    get_settings.cache_clear()

    from app.auth import require_network_access
    from app.main import app

    app.dependency_overrides[require_network_access] = lambda: None

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _login_as_gm(client: TestClient) -> str:
    resp = client.post("/users", json={"username": "gm", "role": "gm"})
    user_id = resp.json()["id"]
    return client.post("/auth/login", json={"user_id": user_id}).json()["token"]


def _login_as_player(client: TestClient, gm_token: str, username: str = "toren") -> int:
    resp = client.post(
        "/users", json={"username": username, "role": "player"}, headers={"Authorization": f"Bearer {gm_token}"}
    )
    return resp.json()["id"]


def _login(client: TestClient, user_id: int) -> str:
    return client.post("/auth/login", json={"user_id": user_id}).json()["token"]


def _set_active_campaign(client: TestClient, gm_headers: dict) -> None:
    campaign_id = client.post("/campaigns", json={"name": "The Sunken Archive"}, headers=gm_headers).json()["id"]
    client.put("/campaigns/active", json={"campaign_id": campaign_id}, headers=gm_headers)


def test_no_active_encounter_by_default(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)

    resp = client.get("/encounters/active", headers=headers)
    assert resp.status_code == 200
    assert resp.json() is None


def test_start_encounter_requires_gm(client: TestClient):
    gm_token = _login_as_gm(client)
    gm_headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, gm_headers)
    player_id = _login_as_player(client, gm_token)
    player_token = _login(client, player_id)

    resp = client.post("/encounters", headers={"Authorization": f"Bearer {player_token}"})
    assert resp.status_code == 403


def test_cannot_start_second_encounter_while_one_is_open(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)

    assert client.post("/encounters", headers=headers).status_code == 201
    resp = client.post("/encounters", headers=headers)
    assert resp.status_code == 409


def test_add_combatant_defaults_from_linked_character(client: TestClient):
    gm_token = _login_as_gm(client)
    gm_headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, gm_headers)
    player_id = _login_as_player(client, gm_token)
    player_token = _login(client, player_id)

    client.put(
        "/characters/me",
        json={
            "name": "Toren Ironfoot",
            "race": "Dwarf",
            "classes": ["Fighter 3"],
            "level": 3,
            "proficiency_bonus": 2,
            "ability_scores": {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
            "hp_current": 28,
            "hp_max": 28,
            "hp_temp": 0,
            "armor_class": 17,
            "passive_perception": 12,
            "currencies": {},
            "inventory": [],
            "spell_slots": {},
            "known_spells": [],
        },
        headers={"Authorization": f"Bearer {player_token}"},
    )

    encounter_id = client.post("/encounters", headers=gm_headers).json()["id"]
    resp = client.post(
        f"/encounters/{encounter_id}/combatants",
        json={"user_id": player_id, "initiative": 15},
        headers=gm_headers,
    )
    assert resp.status_code == 201
    combatant = resp.json()["combatants"][0]
    assert combatant["name"] == "Toren Ironfoot"
    assert combatant["hp_max"] == 28
    assert combatant["armor_class"] == 17


def test_add_monster_combatant_requires_a_name(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)
    encounter_id = client.post("/encounters", headers=headers).json()["id"]

    resp = client.post(f"/encounters/{encounter_id}/combatants", json={"initiative": 8}, headers=headers)
    assert resp.status_code == 400


def test_damage_applied_to_linked_combatant_writes_through_to_character(client: TestClient):
    gm_token = _login_as_gm(client)
    gm_headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, gm_headers)
    player_id = _login_as_player(client, gm_token)
    player_token = _login(client, player_id)
    player_headers = {"Authorization": f"Bearer {player_token}"}

    client.put(
        "/characters/me",
        json={
            "name": "Toren", "race": "", "classes": [], "level": 1, "proficiency_bonus": 2,
            "ability_scores": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
            "hp_current": 20, "hp_max": 20, "hp_temp": 0, "armor_class": 12, "passive_perception": 10,
            "currencies": {}, "inventory": [], "spell_slots": {}, "known_spells": [],
        },
        headers=player_headers,
    )

    encounter_id = client.post("/encounters", headers=gm_headers).json()["id"]
    combatant_id = client.post(
        f"/encounters/{encounter_id}/combatants", json={"user_id": player_id, "initiative": 10}, headers=gm_headers
    ).json()["combatants"][0]["id"]

    resp = client.patch(
        f"/encounters/{encounter_id}/combatants/{combatant_id}", json={"hp_current": 6}, headers=gm_headers
    )
    assert resp.status_code == 200
    assert resp.json()["combatants"][0]["hp_current"] == 6

    character = client.get("/characters/me", headers=player_headers).json()
    assert character["hp_current"] == 6


def test_hp_current_is_clamped_between_zero_and_max(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)
    encounter_id = client.post("/encounters", headers=headers).json()["id"]
    combatant_id = client.post(
        f"/encounters/{encounter_id}/combatants",
        json={"name": "Goblin", "hp_current": 7, "hp_max": 7, "initiative": 5},
        headers=headers,
    ).json()["combatants"][0]["id"]

    resp = client.patch(
        f"/encounters/{encounter_id}/combatants/{combatant_id}", json={"hp_current": -99}, headers=headers
    )
    assert resp.json()["combatants"][0]["hp_current"] == 0


def test_next_turn_wraps_and_increments_round(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)
    encounter_id = client.post("/encounters", headers=headers).json()["id"]
    client.post(f"/encounters/{encounter_id}/combatants", json={"name": "A", "initiative": 20}, headers=headers)
    client.post(f"/encounters/{encounter_id}/combatants", json={"name": "B", "initiative": 10}, headers=headers)

    resp = client.post(f"/encounters/{encounter_id}/next-turn", headers=headers)
    body = resp.json()
    assert body["turn_index"] == 1
    assert body["round"] == 1

    resp = client.post(f"/encounters/{encounter_id}/next-turn", headers=headers)
    body = resp.json()
    assert body["turn_index"] == 0
    assert body["round"] == 2


def test_end_encounter_allows_starting_a_new_one(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)
    encounter_id = client.post("/encounters", headers=headers).json()["id"]

    assert client.post(f"/encounters/{encounter_id}/end", headers=headers).status_code == 204
    assert client.get("/encounters/active", headers=headers).json() is None
    assert client.post("/encounters", headers=headers).status_code == 201


def test_remove_combatant(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)
    encounter_id = client.post("/encounters", headers=headers).json()["id"]
    combatant_id = client.post(
        f"/encounters/{encounter_id}/combatants", json={"name": "Goblin", "initiative": 5}, headers=headers
    ).json()["combatants"][0]["id"]

    resp = client.delete(f"/encounters/{encounter_id}/combatants/{combatant_id}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/encounters/active", headers=headers).json()["combatants"] == []
