"""Tests for User.total_seconds_active - checkpointed at logout (see
app/routers/auth.py) to back the Home dashboard's "time in Lorekeeper" stat.
"""
import dataclasses

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


def test_logout_checkpoints_elapsed_time_onto_the_user(client: TestClient):
    from app.main import app

    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)

    # Back-dates the session's start time by 42 seconds so logout's elapsed
    # computation has something deterministic to checkpoint against, rather
    # than actually sleeping in the test. SessionRecord is frozen, so this
    # replaces the store's own copy with an equivalent record dated earlier.
    store = app.state.sessions
    record = store.get(gm_token)
    store._sessions[gm_token] = dataclasses.replace(record, created_at=record.created_at - 42)

    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {gm_token}"})
    assert resp.status_code == 204

    new_token = _login(client, gm_id)
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"}).json()
    assert me["total_seconds_active"] >= 42


def test_fresh_user_starts_at_zero(client: TestClient):
    gm_id = _register(client, "gm", "gm")
    gm_token = _login(client, gm_id)

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {gm_token}"}).json()
    assert me["total_seconds_active"] == 0


def test_total_accumulates_across_multiple_logins(client: TestClient):
    from app.main import app

    gm_id = _register(client, "gm", "gm")

    for _ in range(2):
        token = _login(client, gm_id)
        store = app.state.sessions
        record = store.get(token)
        store._sessions[token] = dataclasses.replace(record, created_at=record.created_at - 10)
        client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

    final_token = _login(client, gm_id)
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {final_token}"}).json()
    assert me["total_seconds_active"] >= 20
