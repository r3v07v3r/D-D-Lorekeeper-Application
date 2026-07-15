"""Standalone entrypoint for the PyInstaller-frozen backend executable.

app/main.py only defines the FastAPI `app` object - this script is what
actually runs it, so PyInstaller has something executable to freeze (see
build_backend.py). Electron spawns this compiled executable directly in
production; in development, Electron (or the developer) instead runs this
same script against the source tree.
"""
import os
from pathlib import Path

import uvicorn

from app.main import app
from app.tls import ensure_certificate

if __name__ == "__main__":
    # Import the app object directly (rather than uvicorn.run("app.main:app", ...))
    # since string-based dynamic import resolution is one more thing that can
    # go wrong inside a PyInstaller-frozen module search path - passing the
    # object avoids that class of failure entirely.
    port = int(os.environ.get("LOREKEEPER_PORT", "8000"))
    config_dir = Path(os.environ.get("LOREKEEPER_CONFIG_DIR", "."))
    cert_path, key_path = ensure_certificate(config_dir)

    # 0.0.0.0 (not 127.0.0.1): the GM's machine needs to accept connections
    # from players elsewhere on the LAN/internet, not just from its own
    # Electron frontend. This does not by itself expose the app publicly -
    # that still requires the GM's router to forward the port (see the
    # Settings UI's port-forwarding instructions). See
    # app.auth.require_network_access for the actual auth boundary this
    # depends on, and app.tls for why this is HTTPS with a self-signed,
    # fingerprint-pinned certificate rather than plain HTTP.
    uvicorn.run(app, host="0.0.0.0", port=port, ssl_certfile=str(cert_path), ssl_keyfile=str(key_path))
