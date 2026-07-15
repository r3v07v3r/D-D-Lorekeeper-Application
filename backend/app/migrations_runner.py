"""Runs Alembic migrations at startup, in place of Base.metadata.create_all().

Handles the one-time transition for existing installs: earlier versions of
this app created tables directly via create_all() with no alembic_version
tracking table at all. On such an install, running `alembic upgrade head`
from scratch would try to CREATE TABLE against tables that already exist
and fail. Instead, if the DB already has the app's tables but no
alembic_version table, this stamps it at the baseline revision (which
autogenerate produced from that exact schema) without re-running it - then
any migrations added after the baseline apply normally via upgrade() on
every subsequent startup, for both old and new installs alike.
"""
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    # PyInstaller (onefile) extracts bundled data files under sys._MEIPASS
    # at runtime - see build_backend.py's --add-data flags, which bundle
    # alembic.ini and migrations/ alongside the frozen executable's code.
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def run_migrations(database_url: str) -> None:
    backend_root = _backend_root()
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)

    engine = create_engine(database_url)
    try:
        existing_tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    if "alembic_version" not in existing_tables and "users" in existing_tables:
        logger.info("Existing pre-Alembic database detected - stamping baseline revision instead of re-creating tables")
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")
