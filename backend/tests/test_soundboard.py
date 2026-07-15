"""Tests for the soundboard: validation helpers (pure functions) plus an
end-to-end upload/list/update/delete/GM-gating pass through the real app.
"""
import base64
import io
import wave

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.soundboard import MAX_CLIP_BYTES, SoundClipError, decode_clip, delete_clip_file, save_clip_file, validate_extension


def _tiny_wav_base64() -> str:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b"\x00\x00" * 100)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---- validate_extension ----

def test_validate_extension_accepts_allowed_types():
    assert validate_extension("boom.mp3") == ".mp3"
    assert validate_extension("Thunder.WAV") == ".wav"


def test_validate_extension_rejects_unknown_type():
    with pytest.raises(SoundClipError):
        validate_extension("script.exe")


def test_validate_extension_rejects_no_extension():
    with pytest.raises(SoundClipError):
        validate_extension("noextension")


# ---- decode_clip ----

def test_decode_clip_accepts_valid_base64():
    data = decode_clip(base64.b64encode(b"fake-audio-bytes").decode())
    assert data == b"fake-audio-bytes"


def test_decode_clip_rejects_invalid_base64():
    with pytest.raises(SoundClipError):
        decode_clip("not valid base64!!! ###")


def test_decode_clip_rejects_empty():
    with pytest.raises(SoundClipError):
        decode_clip(base64.b64encode(b"").decode())


def test_decode_clip_rejects_oversized():
    oversized = base64.b64encode(b"x" * (MAX_CLIP_BYTES + 1)).decode()
    with pytest.raises(SoundClipError):
        decode_clip(oversized)


# ---- save/delete_clip_file ----

def test_save_and_delete_clip_file(tmp_path):
    filename = save_clip_file(tmp_path, ".mp3", b"audio-data")
    assert filename.endswith(".mp3")
    assert (tmp_path / filename).read_bytes() == b"audio-data"

    delete_clip_file(tmp_path, filename)
    assert not (tmp_path / filename).exists()


def test_delete_missing_file_is_a_noop(tmp_path):
    delete_clip_file(tmp_path, "does-not-exist.mp3")  # must not raise


# ---- End-to-end through the real app ----

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Spins up the real app against an isolated, temp-file SQLite DB.

    app.database.engine/SessionLocal are module-level globals built once at
    that module's first import (likely already triggered by an earlier test
    file's collection-time imports, e.g. test_notes_visibility.py), so
    setting DATABASE_URL here would be too late to matter - by the time this
    fixture runs, that engine already exists, bound to whatever the default
    was. Patching the already-created engine/SessionLocal objects directly
    (before app.main - and therefore its own `from app.database import
    engine, SessionLocal` - gets imported for the first time here) is what
    actually keeps this test from reading/writing the real backend/
    directory's lorekeeper.db.
    """
    import app.database as database_module

    test_engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database_module, "engine", test_engine)
    monkeypatch.setattr(database_module, "SessionLocal", TestSessionLocal)

    # main.py's own on_startup() also calls Base.metadata.create_all(), but
    # against *its* frozen `engine` name - which, across this whole test
    # file, only reflects whichever test happened to trigger app.main's
    # first-ever import (see docstring above). Creating the schema directly
    # against this test's own engine here makes each test self-sufficient
    # regardless of that quirk.
    database_module.Base.metadata.create_all(bind=test_engine)

    monkeypatch.setenv("LOREKEEPER_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("AUDIO_STORAGE_DIR", str(tmp_path / "recordings"))

    # get_settings() is lru_cache'd with no arguments and was almost
    # certainly already called (and cached) at collection time by some
    # earlier test file's import chain, before the env vars above were set -
    # clearing it forces main.py's own module-level `settings = get_settings()`
    # (evaluated at the `from app.main import app` below) to read the
    # env vars this fixture just set, instead of a stale cached Settings().
    from app.config import get_settings
    get_settings.cache_clear()

    from app.auth import require_network_access
    from app.main import app  # first import in this test session - picks up the patches above

    # require_network_access (see test_network_access.py, which covers it
    # directly) only allows loopback callers before a passphrase is set -
    # TestClient's requests report a fake "testclient" host, not 127.0.0.1,
    # so bootstrapping a GM here would otherwise 403 for reasons unrelated to
    # anything this file is testing.
    app.dependency_overrides[require_network_access] = lambda: None

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _login_as_gm(client: TestClient) -> str:
    resp = client.post("/users", json={"username": "gm", "role": "gm"})
    user_id = resp.json()["id"]
    token = client.post("/auth/login", json={"user_id": user_id}).json()["token"]
    return token


def test_upload_list_update_delete_roundtrip(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/soundboard",
        headers=headers,
        json={"name": "Thunder", "filename": "thunder.wav", "content_base64": _tiny_wav_base64(), "volume": 0.8},
    )
    assert resp.status_code == 201, resp.text
    clip = resp.json()
    assert clip["name"] == "Thunder"
    assert clip["volume"] == 0.8

    resp = client.get("/soundboard", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.patch(f"/soundboard/{clip['id']}", headers=headers, json={"name": "Big Thunder", "volume": 1.0})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Big Thunder"
    assert resp.json()["volume"] == 1.0

    resp = client.delete(f"/soundboard/{clip['id']}", headers=headers)
    assert resp.status_code == 204

    resp = client.get("/soundboard", headers=headers)
    assert resp.json() == []


def test_upload_rejects_bad_extension(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/soundboard",
        headers=headers,
        json={"name": "Evil", "filename": "evil.exe", "content_base64": _tiny_wav_base64()},
    )
    assert resp.status_code == 400


def test_player_cannot_manage_soundboard(client: TestClient):
    gm_token = _login_as_gm(client)
    resp = client.post(
        "/users",
        headers={"Authorization": f"Bearer {gm_token}"},
        json={"username": "alice", "role": "player"},
    )
    player_token = client.post("/auth/login", json={"user_id": resp.json()["id"]}).json()["token"]
    player_headers = {"Authorization": f"Bearer {player_token}"}

    assert client.get("/soundboard", headers=player_headers).status_code == 403
    assert (
        client.post(
            "/soundboard",
            headers=player_headers,
            json={"name": "x", "filename": "x.mp3", "content_base64": _tiny_wav_base64()},
        ).status_code
        == 403
    )


def test_play_requires_bot_connected_to_voice(client: TestClient):
    token = _login_as_gm(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/soundboard",
        headers=headers,
        json={"name": "Thunder", "filename": "thunder.wav", "content_base64": _tiny_wav_base64()},
    )
    clip_id = resp.json()["id"]

    # No Discord bot token configured in this test, so no voice_client is
    # ever connected - playing should fail with a clear, expected error
    # rather than a crash.
    resp = client.post(f"/soundboard/{clip_id}/play", headers=headers)
    assert resp.status_code == 409
