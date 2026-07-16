"""Tests for the Campaign entity: CRUD, the "active campaign" concept that
gates session creation/listing, and the GM-only write restrictions (see
app/routers/campaigns.py and app/models.py's Campaign docstring).
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


def _login_as_player(client: TestClient, gm_token: str, username: str = "toren") -> str:
    resp = client.post("/users", json={"username": username, "role": "player"}, headers={"Authorization": f"Bearer {gm_token}"})
    user_id = resp.json()["id"]
    return client.post("/auth/login", json={"user_id": user_id}).json()["token"]


def test_create_and_list_campaigns(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/campaigns", json={"name": "The Sunken Archive"}, headers=headers)
    client.post("/campaigns", json={"name": "Curse of the Old Mill"}, headers=headers)

    names = {c["name"] for c in client.get("/campaigns", headers=headers).json()}
    assert names == {"The Sunken Archive", "Curse of the Old Mill"}


def test_player_cannot_create_campaign(client: TestClient):
    gm_token = _login_as_gm(client)
    player_token = _login_as_player(client, gm_token)

    resp = client.post("/campaigns", json={"name": "Nope"}, headers={"Authorization": f"Bearer {player_token}"})
    assert resp.status_code == 403


def test_create_campaign_rejects_blank_name(client: TestClient):
    token = _login_as_gm(client)
    resp = client.post("/campaigns", json={"name": "   "}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_rename_campaign(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}
    campaign_id = client.post("/campaigns", json={"name": "Old Name"}, headers=headers).json()["id"]

    resp = client.patch(f"/campaigns/{campaign_id}", json={"name": "New Name"}, headers=headers)
    assert resp.json()["name"] == "New Name"


def test_no_active_campaign_by_default(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/campaigns", json={"name": "A"}, headers=headers)
    client.post("/campaigns", json={"name": "B"}, headers=headers)

    # Two campaigns exist and neither is marked active - genuinely ambiguous,
    # so nothing should be auto-selected (contrast with the single-campaign
    # auto-select convenience in app/main.py's on_startup).
    resp = client.get("/campaigns/active", headers=headers)
    assert resp.json() is None


def test_set_active_campaign(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}
    campaign_id = client.post("/campaigns", json={"name": "The Sunken Archive"}, headers=headers).json()["id"]

    client.put("/campaigns/active", json={"campaign_id": campaign_id}, headers=headers)
    active = client.get("/campaigns/active", headers=headers).json()
    assert active["id"] == campaign_id


def test_player_cannot_set_active_campaign(client: TestClient):
    gm_token = _login_as_gm(client)
    campaign_id = client.post(
        "/campaigns", json={"name": "The Sunken Archive"}, headers={"Authorization": f"Bearer {gm_token}"}
    ).json()["id"]
    player_token = _login_as_player(client, gm_token)

    resp = client.put(
        "/campaigns/active", json={"campaign_id": campaign_id}, headers={"Authorization": f"Bearer {player_token}"}
    )
    assert resp.status_code == 403


def test_session_creation_requires_active_campaign(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/sessions", json={"session_number": 1, "date": "2026-07-01"}, headers=headers)
    assert resp.status_code == 400


def test_session_created_under_active_campaign(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}
    campaign_id = client.post("/campaigns", json={"name": "The Sunken Archive"}, headers=headers).json()["id"]
    client.put("/campaigns/active", json={"campaign_id": campaign_id}, headers=headers)

    resp = client.post("/sessions", json={"session_number": 1, "date": "2026-07-01"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["campaign_id"] == campaign_id
    assert resp.json()["campaign_name"] == "The Sunken Archive"


def test_sessions_list_scoped_to_active_campaign(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}
    campaign_a = client.post("/campaigns", json={"name": "A"}, headers=headers).json()["id"]
    campaign_b = client.post("/campaigns", json={"name": "B"}, headers=headers).json()["id"]

    client.put("/campaigns/active", json={"campaign_id": campaign_a}, headers=headers)
    client.post("/sessions", json={"session_number": 1, "date": "2026-07-01"}, headers=headers)

    client.put("/campaigns/active", json={"campaign_id": campaign_b}, headers=headers)
    client.post("/sessions", json={"session_number": 1, "date": "2026-07-08"}, headers=headers)

    sessions_b = client.get("/sessions", headers=headers).json()
    assert len(sessions_b) == 1
    assert sessions_b[0]["campaign_id"] == campaign_b

    client.put("/campaigns/active", json={"campaign_id": campaign_a}, headers=headers)
    sessions_a = client.get("/sessions", headers=headers).json()
    assert len(sessions_a) == 1
    assert sessions_a[0]["campaign_id"] == campaign_a
