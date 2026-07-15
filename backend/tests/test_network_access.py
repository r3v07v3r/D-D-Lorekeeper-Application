"""Tests for require_network_access: the gate on the two endpoints reachable
with no session token (GET /users, POST /auth/login) now that the backend
can be reached from other machines on a LAN, not just the GM's own PC.

The dependency is called directly (bypassing the FastAPI TestClient's HTTP
layer) so the "client host" seen by the check can be controlled precisely -
TestClient reports a fixed fake host ("testclient") that doesn't reflect
real loopback-vs-remote distinctions.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth import require_network_access
from app.config import Settings
from app.runtime_config import RuntimeConfigStore


@pytest.fixture
def base_settings():
    return Settings(discord_bot_token="", openai_api_key="")


def make_request(client_host: str | None, runtime_config: RuntimeConfigStore) -> Request:
    scope = {
        "type": "http",
        "client": (client_host, 12345) if client_host else None,
        "app": SimpleNamespace(state=SimpleNamespace(runtime_config=runtime_config)),
        "headers": [],
    }
    return Request(scope)


def test_loopback_allowed_before_passphrase_set(tmp_path, base_settings):
    config = RuntimeConfigStore(tmp_path, base=base_settings)
    request = make_request("127.0.0.1", config)

    require_network_access(request, x_campaign_passphrase=None)  # must not raise


def test_ipv6_loopback_allowed_before_passphrase_set(tmp_path, base_settings):
    config = RuntimeConfigStore(tmp_path, base=base_settings)
    request = make_request("::1", config)

    require_network_access(request, x_campaign_passphrase=None)  # must not raise


def test_remote_host_rejected_before_passphrase_set(tmp_path, base_settings):
    config = RuntimeConfigStore(tmp_path, base=base_settings)
    request = make_request("192.168.1.50", config)

    with pytest.raises(HTTPException) as exc_info:
        require_network_access(request, x_campaign_passphrase=None)
    assert exc_info.value.status_code == 403


def test_remote_host_allowed_with_correct_passphrase(tmp_path, base_settings):
    config = RuntimeConfigStore(tmp_path, base=base_settings)
    config.set_passphrase("open-sesame")
    request = make_request("192.168.1.50", config)

    require_network_access(request, x_campaign_passphrase="open-sesame")  # must not raise


def test_remote_host_rejected_with_wrong_passphrase(tmp_path, base_settings):
    config = RuntimeConfigStore(tmp_path, base=base_settings)
    config.set_passphrase("open-sesame")
    request = make_request("192.168.1.50", config)

    with pytest.raises(HTTPException) as exc_info:
        require_network_access(request, x_campaign_passphrase="wrong-guess")
    assert exc_info.value.status_code == 401


def test_loopback_also_requires_passphrase_once_one_is_set(tmp_path, base_settings):
    """Once a passphrase exists, even the GM's own machine must supply it -
    no permanent loopback exemption once the GM has opted into sharing
    the server, so behavior stays consistent and easy to reason about.
    """
    config = RuntimeConfigStore(tmp_path, base=base_settings)
    config.set_passphrase("open-sesame")
    request = make_request("127.0.0.1", config)

    with pytest.raises(HTTPException) as exc_info:
        require_network_access(request, x_campaign_passphrase=None)
    assert exc_info.value.status_code == 401
