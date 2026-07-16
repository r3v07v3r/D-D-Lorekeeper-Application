"""Tests for GET /users/presence - the app-level "connected" signal behind
the dashboard's grey/lit sidebar avatars (see app/auth.py's
SessionStore.connected_user_ids and app/routers/users.py:get_presence).
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


def _register(client: TestClient, username: str, role: str, gm_token: str | None = None) -> int:
    headers = {"Authorization": f"Bearer {gm_token}"} if gm_token else {}
    resp = client.post("/users", json={"username": username, "role": role}, headers=headers)
    return resp.json()["id"]


def _login(client: TestClient, user_id: int) -> str:
    return client.post("/auth/login", json={"user_id": user_id}).json()["token"]


def test_logged_in_user_shows_as_connected(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)

    presence = client.get("/users/presence", headers={"Authorization": f"Bearer {gm_token}"}).json()

    assert presence[str(gm_id)] is True


def test_registered_but_not_logged_in_user_shows_as_disconnected(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)
    player_id = _register(client, "toren", "player", gm_token)

    presence = client.get("/users/presence", headers={"Authorization": f"Bearer {gm_token}"}).json()

    assert presence[str(player_id)] is False


def test_player_shows_connected_once_logged_in(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)
    player_id = _register(client, "toren", "player", gm_token)
    _login(client, player_id)

    presence = client.get("/users/presence", headers={"Authorization": f"Bearer {gm_token}"}).json()

    assert presence[str(player_id)] is True


def test_presence_requires_authentication(client: TestClient):
    resp = client.get("/users/presence")
    assert resp.status_code == 401


# ---- GET /users/voice-presence - real Discord voice presence ----
#
# BotState.voice_member_discord_ids (see app/state.py) is normally kept live
# by app/bot/client.py's on_voice_state_update handler and seeded by
# app/bot/controller.py:join_channel - no real Discord bot runs in these
# tests, so these set it directly to exercise get_voice_presence's own
# matching logic in isolation.


def test_voice_presence_true_when_bot_state_reports_the_users_discord_id(client: TestClient):
    from app.main import app

    resp = client.post("/users", json={"username": "gm", "role": "gm", "discord_id": "111"})
    gm_id = resp.json()["id"]
    gm_token = _login(client, gm_id)

    app.state.bot_state.voice_member_discord_ids = {"111"}

    presence = client.get("/users/voice-presence", headers={"Authorization": f"Bearer {gm_token}"}).json()
    assert presence[str(gm_id)] is True


def test_voice_presence_false_when_not_in_bot_states_set(client: TestClient):
    from app.main import app

    resp = client.post("/users", json={"username": "gm", "role": "gm", "discord_id": "222"})
    gm_id = resp.json()["id"]
    gm_token = _login(client, gm_id)

    app.state.bot_state.voice_member_discord_ids = set()

    presence = client.get("/users/voice-presence", headers={"Authorization": f"Bearer {gm_token}"}).json()
    assert presence[str(gm_id)] is False


def test_voice_presence_false_with_no_discord_id_on_file(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)

    presence = client.get("/users/voice-presence", headers={"Authorization": f"Bearer {gm_token}"}).json()
    assert presence[str(gm_id)] is False


def test_voice_presence_requires_authentication(client: TestClient):
    resp = client.get("/users/voice-presence")
    assert resp.status_code == 401
