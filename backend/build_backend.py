"""Builds the standalone backend executable with PyInstaller.

Run from backend/ with the venv activated (after `pip install -r
requirements-build.txt`):
    python build_backend.py

Produces dist/lorekeeper-backend(.exe), a single-file executable with no
Python runtime dependency on the target machine. This exact command (onefile,
entrypoint run.py) was used to verify, during development, that:
  - the app's full import graph (including py-cord's voice/PyNaCl bits)
    freezes and runs correctly (see project risk #5), and
  - a subprocess call out to `ffmpeg` still works from inside the frozen exe.
ffmpeg itself is NOT bundled here - it remains an external runtime
requirement that must be on PATH (see README/risk #5). Bundling a
per-platform ffmpeg binary would be a reasonable future improvement but
adds real size/licensing complexity that's out of scope for now.
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def _add_data(src: Path, dest: str) -> str:
    # PyInstaller's --add-data separator is OS-specific (';' on Windows, ':'
    # elsewhere) - os.pathsep gets this right regardless of build platform.
    # The source must be absolute: --specpath below moves where PyInstaller
    # resolves *relative* paths from, which broke a relative "alembic.ini"
    # source (it looked for it under build_tmp/ instead of this directory).
    return f"{src}{os.pathsep}{dest}"


def main() -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--name", "lorekeeper-backend",
            "--distpath", "dist",
            "--workpath", "build_tmp",
            "--specpath", "build_tmp",
            # Alembic reads these at runtime (app/migrations_runner.py) to
            # apply schema migrations - they're data files it execs by path,
            # not a normal importable package, so PyInstaller's own import
            # analysis won't pick them up on its own and they must be listed
            # explicitly. Extracted under sys._MEIPASS at runtime.
            "--add-data", _add_data(BACKEND_DIR / "alembic.ini", "."),
            "--add-data", _add_data(BACKEND_DIR / "migrations", "migrations"),
            "run.py",
        ],
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
