"""Database engine configuration for the game service."""

import sqlite3
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
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


def configure_sqlite_engine(database_engine: Engine) -> None:
    """Configure SQLite BEGIN behavior and WAL; leave other dialects alone."""
    if database_engine.dialect.name != "sqlite":
        return

    @event.listens_for(database_engine, "connect")
    def prepare_connection(dbapi_connection: object, connection_record: object) -> None:
        del connection_record
        if isinstance(dbapi_connection, sqlite3.Connection):
            dbapi_connection.isolation_level = None
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            finally:
                cursor.close()

    @event.listens_for(database_engine, "begin")
    def begin_transaction(connection: Connection) -> None:
        if connection.dialect.name != "sqlite":
            return
        mode = (
            "BEGIN IMMEDIATE"
            if connection.get_execution_options().get("sqlite_write_intent")
            else "BEGIN"
        )
        connection.exec_driver_sql(mode)


if DATABASE_URL.startswith("sqlite:"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    configure_sqlite_engine(engine)
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base for game-owned SQLAlchemy models."""


def get_db() -> Generator[Session, None, None]:
    """Provide a transaction-scoped database session to a request."""
    with SessionLocal() as session:
        yield session
