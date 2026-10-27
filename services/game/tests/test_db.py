"""Dialect boundaries for SQLite's explicit transaction configuration."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, ExecutionContext

from app.db import configure_sqlite_engine


@pytest.mark.parametrize("write_intent", [False, True])
def test_transaction_configuration_on_selected_database(
    tmp_path: Path, write_intent: bool
) -> None:
    """SQLite configuration is safe even when called on the PostgreSQL fixture."""
    engine = create_engine(
        os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'transactions.db'}")
    )
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    configure_sqlite_engine(engine)
    try:
        with engine.connect().execution_options(
            sqlite_write_intent=write_intent
        ) as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            connection.commit()
        if engine.dialect.name == "sqlite":
            assert statements == [
                "BEGIN IMMEDIATE" if write_intent else "BEGIN",
                "SELECT 1",
            ]
        else:
            assert statements == ["SELECT 1"]
    finally:
        engine.dispose()


@pytest.mark.parametrize("configure_first", [False, True])
def test_non_sqlite_dialect_never_emits_sqlite_begin(
    monkeypatch: pytest.MonkeyPatch, configure_first: bool
) -> None:
    """Check the dialect guard locally, both before and after listener setup."""
    engine = create_engine("sqlite://")
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    if configure_first:
        configure_sqlite_engine(engine)
    # Use SQLite transport to exercise the non-SQLite guard without a server.
    monkeypatch.setattr(engine.dialect, "name", "postgresql")
    if not configure_first:
        configure_sqlite_engine(engine)
    try:
        with engine.connect().execution_options(sqlite_write_intent=True) as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            connection.commit()
        assert statements == ["SELECT 1"]
    finally:
        engine.dispose()
