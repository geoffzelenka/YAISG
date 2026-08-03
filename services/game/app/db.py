"""Database engine configuration for the game service."""

import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


def _ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent directory for a relative SQLite database path."""
    prefix = "sqlite:///"
    is_relative_sqlite = database_url.startswith(
        prefix
    ) and not database_url.startswith("sqlite:////")
    if is_relative_sqlite:
        database_path = Path(database_url.removeprefix(prefix))
        database_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(DATABASE_URL)
if DATABASE_URL.startswith("sqlite:"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base for game-owned SQLAlchemy models."""


async def get_db() -> AsyncGenerator[Session, None]:
    """Provide a transaction-scoped database session to a request."""
    with SessionLocal() as session:
        yield session


@event.listens_for(engine, "connect")
def enable_sqlite_wal(dbapi_connection: object, connection_record: object) -> None:
    """Enable WAL journaling for each SQLite connection."""
    del connection_record
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()
