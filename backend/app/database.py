"""SQLAlchemy engine/session setup.

Phase 1 uses Base.metadata.create_all() for schema creation. Alembic is
intentionally NOT included yet (project risk #6) - it will be scaffolded for
real once the schema has stabilized, rather than listed as a dependency and
left unwired.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# check_same_thread=False is required for SQLite when the connection is used
# across the async FastAPI request/response cycle and background bot tasks.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
