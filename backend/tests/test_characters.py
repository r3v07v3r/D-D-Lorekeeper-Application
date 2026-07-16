"""Tests for the persisted Character model and its endpoints - manual
create/edit, long rest, and the GM party overview (see app/models.py's
Character and app/routers/characters.py). There were no tests for this
router before Phase E added manual character entry alongside D&D Beyond
sync onto the same table.
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


def _register(client: TestClient, username: str, role: str, gm_token: str | None = None, **extra) -> int:
    headers = {"Authorization": f"Bearer {gm_token}"} if gm_token else {}
    resp = client.post("/users", json={"username": username, "role": role, **extra}, headers=headers)
    return resp.json()["id"]


def _login(client: TestClient, user_id: int) -> str:
    return client.post("/auth/login", json={"user_id": user_id}).json()["token"]


_CHARACTER_PAYLOAD = {
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
    "currencies": {"gp": 15},
    "inventory": [{"name": "Longsword", "quantity": 1, "equipped": True}],
    "spell_slots": {},
    "known_spells": [],
}


def test_no_character_yet_is_404(client: TestClient):
    player_id = _register(client, "toren", "player")
    token = _login(client, player_id)

    resp = client.get("/characters/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_create_and_fetch_manual_character(client: TestClient):
    player_id = _register(client, "toren", "player")
    token = _login(client, player_id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/characters/me", json=_CHARACTER_PAYLOAD, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "manual"
    assert body["name"] == "Toren Ironfoot"
    assert body["armor_class_is_estimate"] is False
    assert body["ability_modifiers"]["STR"] == 3  # (16-10)//2

    resp = client.get("/characters/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Toren Ironfoot"


def test_editing_a_dndbeyond_linked_character_is_rejected(client: TestClient):
    player_id = _register(client, "toren", "player", dnd_beyond_character_id="12345")
    token = _login(client, player_id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/characters/me", json=_CHARACTER_PAYLOAD, headers=headers)
    assert resp.status_code == 409


def test_long_rest_restores_hp_and_spell_slots(client: TestClient):
    player_id = _register(client, "toren", "player")
    token = _login(client, player_id)
    headers = {"Authorization": f"Bearer {token}"}

    payload = dict(_CHARACTER_PAYLOAD, hp_current=1, spell_slots={"1": {"current": 0, "max": 4}})
    client.put("/characters/me", json=payload, headers=headers)

    resp = client.post("/characters/me/rest", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hp_current"] == body["hp_max"] == 28
    assert body["spell_slots"]["1"]["current"] == 4


def test_rest_with_no_character_is_404(client: TestClient):
    player_id = _register(client, "toren", "player")
    token = _login(client, player_id)

    resp = client.post("/characters/me/rest", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_party_overview_includes_manual_characters(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)
    player_id = _register(client, "toren", "player", gm_token)
    player_token = _login(client, player_id)
    client.put("/characters/me", json=_CHARACTER_PAYLOAD, headers={"Authorization": f"Bearer {player_token}"})

    resp = client.get("/characters/party", headers={"Authorization": f"Bearer {gm_token}"})
    assert resp.status_code == 200
    party = resp.json()
    assert len(party) == 1
    assert party[0]["character"]["name"] == "Toren Ironfoot"


def test_party_overview_is_gm_only(client: TestClient):
    player_id = _register(client, "toren", "player")
    token = _login(client, player_id)

    resp = client.get("/characters/party", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_get_my_character_only_returns_own_character(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)
    alice_id = _register(client, "alice", "player", gm_token)
    bob_id = _register(client, "bob", "player", gm_token)
    alice_token = _login(client, alice_id)
    bob_token = _login(client, bob_id)

    client.put("/characters/me", json=_CHARACTER_PAYLOAD, headers={"Authorization": f"Bearer {alice_token}"})

    resp = client.get("/characters/me", headers={"Authorization": f"Bearer {bob_token}"})
    assert resp.status_code == 404
