"""Tests for the shared, polled dice-roll log (see app/models.py:RollLogEntry
and app/routers/rolls.py) - any authenticated user can post/read rolls for
the active campaign, scoped so a since_id poll only returns new entries.
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


def _set_active_campaign(client: TestClient, gm_headers: dict) -> None:
    campaign_id = client.post("/campaigns", json={"name": "The Sunken Archive"}, headers=gm_headers).json()["id"]
    client.put("/campaigns/active", json={"campaign_id": campaign_id}, headers=gm_headers)


def test_roll_without_active_campaign_is_rejected(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}

    resp = client.post("/rolls", json={"summary": "d20 [12]", "total": 12}, headers=headers)
    assert resp.status_code == 400


def test_post_and_list_rolls(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)

    resp = client.post("/rolls", json={"summary": "d20 [17] +3 = 20", "total": 20}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "gm"
    assert body["total"] == 20

    rolls = client.get("/rolls", headers=headers).json()
    assert len(rolls) == 1
    assert rolls[0]["summary"] == "d20 [17] +3 = 20"


def test_since_id_only_returns_newer_rolls(client: TestClient):
    gm_token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {gm_token}"}
    _set_active_campaign(client, headers)

    first_id = client.post("/rolls", json={"summary": "roll 1", "total": 1}, headers=headers).json()["id"]
    client.post("/rolls", json={"summary": "roll 2", "total": 2}, headers=headers)

    rolls = client.get(f"/rolls?since_id={first_id}", headers=headers).json()
    assert len(rolls) == 1
    assert rolls[0]["summary"] == "roll 2"


def test_rolls_require_authentication(client: TestClient):
    resp = client.get("/rolls")
    assert resp.status_code == 401
