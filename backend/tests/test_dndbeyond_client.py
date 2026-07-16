"""Tests for app.dndbeyond.client's error handling - in particular the 403
case, which was previously surfaced as an opaque "HTTP 403" with no
indication of the fix (the character's D&D Beyond sharing setting isn't
Public). Reproduced live against a real private character during
development before writing this fix - see git history for that repro.
"""
import asyncio

import httpx
import pytest

from app.dndbeyond.client import DndBeyondError, fetch_character_raw


@pytest.fixture
def patch_http_client(monkeypatch):
    def _patch(status_code: int, json_body: dict):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json=json_body)

        transport = httpx.MockTransport(handler)

        class FakeAsyncClient(httpx.AsyncClient):
            def __init__(self, *args, **kwargs):
                kwargs["transport"] = transport
                super().__init__(*args, **kwargs)

        monkeypatch.setattr("app.dndbeyond.client.httpx.AsyncClient", FakeAsyncClient)

    return _patch


def test_success_returns_data(patch_http_client):
    patch_http_client(200, {"success": True, "message": "ok", "data": {"id": 1}})
    data = asyncio.run(fetch_character_raw("1"))
    assert data == {"id": 1}


def test_403_gives_actionable_sharing_message(patch_http_client):
    patch_http_client(403, {"success": False, "message": "Unauthorized Access Attempt."})
    with pytest.raises(DndBeyondError) as exc_info:
        asyncio.run(fetch_character_raw("123096288"))
    assert "sharing" in str(exc_info.value).lower()
    assert "public" in str(exc_info.value).lower()


def test_not_found_gives_generic_message(patch_http_client):
    patch_http_client(200, {"success": False, "message": "The resource requested was not found."})
    with pytest.raises(DndBeyondError) as exc_info:
        asyncio.run(fetch_character_raw("999"))
    assert "999" in str(exc_info.value)


def test_other_http_error_reports_status_code(patch_http_client):
    patch_http_client(500, {})
    with pytest.raises(DndBeyondError) as exc_info:
        asyncio.run(fetch_character_raw("1"))
    assert "500" in str(exc_info.value)
