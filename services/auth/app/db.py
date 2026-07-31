"""Database engine configuration for the authentication service."""

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event

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
