"""Best-effort LAN and public IP detection, so the GM can see what address
to share with players without having to go find it themselves.
"""
import logging
import socket
import time

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_public_ip_cache: tuple[float, str | None] | None = None


def detect_lan_ip() -> str | None:
    """Returns this machine's LAN-facing IP, or None if it can't be determined
    (e.g. no network connectivity). Uses the standard "connect a UDP socket
    to a public address" trick to ask the OS which local interface/IP would
    be used for outbound traffic - no packets are actually sent for UDP
    connect(), so this works offline-safe and doesn't depend on 8.8.8.8
    being reachable.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def detect_public_ip() -> str | None:
    """Returns this machine's internet-facing IP (i.e. the address a player
    connecting over the internet would need, assuming the GM's router is
    forwarding the port to this machine), or None if it can't be reached.

    Cached for a few minutes so opening the Settings tab repeatedly doesn't
    hit an external service (or block on its timeout while offline) every
    time - this is a GM-facing convenience display, not something that needs
    to be live-accurate to the second.

    Note this is the *router's* public IP, not proof that anything is
    actually forwarded to this machine - the GM still needs to configure
    port forwarding for their router (see Settings UI copy) for internet
    players to actually reach this backend.
    """
    global _public_ip_cache

    now = time.monotonic()
    if _public_ip_cache is not None and now - _public_ip_cache[0] < _CACHE_TTL_SECONDS:
        return _public_ip_cache[1]

    ip = _fetch_public_ip()
    _public_ip_cache = (now, ip)
    return ip


def _fetch_public_ip() -> str | None:
    try:
        response = httpx.get("https://api.ipify.org", timeout=3.0)
        response.raise_for_status()
        ip = response.text.strip()
        return ip or None
    except httpx.HTTPError as exc:
        logger.warning("Could not detect public IP: %s", exc)
        return None
