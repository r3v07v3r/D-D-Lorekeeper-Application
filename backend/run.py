"""Standalone entrypoint for the PyInstaller-frozen backend executable.

app/main.py only defines the FastAPI `app` object - this script is what
actually runs it, so PyInstaller has something executable to freeze (see
build_backend.py). Electron spawns this compiled executable directly in
production; in development, Electron (or the developer) instead runs
`uvicorn app.main:app --reload` against the source tree.
"""
import os

import uvicorn

from app.main import app

if __name__ == "__main__":
    # Import the app object directly (rather than uvicorn.run("app.main:app", ...))
    # since string-based dynamic import resolution is one more thing that can
    # go wrong inside a PyInstaller-frozen module search path - passing the
    # object avoids that class of failure entirely.
    port = int(os.environ.get("LOREKEEPER_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
