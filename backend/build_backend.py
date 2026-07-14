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
import subprocess
import sys

def main() -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--name", "lorekeeper-backend",
            "--distpath", "dist",
            "--workpath", "build_tmp",
            "--specpath", "build_tmp",
            "run.py",
        ],
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
