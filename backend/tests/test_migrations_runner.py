"""Tests for app.migrations_runner: the three states a database can be in
at startup - genuinely fresh, an existing pre-Alembic install (created by
an earlier version of this app via plain create_all(), no alembic_version
table), and one already tracked by Alembic - all need to end up at the
same schema without erroring.
"""
from sqlalchemy import create_engine, inspect

from app.database import Base
from app.migrations_runner import run_migrations

EXPECTED_TABLES = {"alembic_version", "campaigns", "notes", "session_logs", "sound_clips", "users"}


def _tables(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_fresh_database_gets_full_schema(tmp_path):
    url = f"sqlite:///{tmp_path}/fresh.db"
    run_migrations(url)
    assert _tables(url) == EXPECTED_TABLES


def test_existing_pre_alembic_database_is_stamped_not_recreated(tmp_path):
    url = f"sqlite:///{tmp_path}/existing.db"
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)  # simulates an install predating Alembic
    engine.dispose()

    run_migrations(url)  # must not try (and fail) to CREATE TABLE over existing ones

    assert _tables(url) == EXPECTED_TABLES


def test_rerunning_migrations_is_a_safe_no_op(tmp_path):
    url = f"sqlite:///{tmp_path}/rerun.db"
    run_migrations(url)
    run_migrations(url)  # must not raise
    assert _tables(url) == EXPECTED_TABLES
