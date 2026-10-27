"""Destructively recreate both development databases, then migrate to head."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

ROOT = Path(__file__).resolve().parents[1]


def database_url(service: str) -> URL:
    """Read the configured database URL for one service."""
    return make_url(
        os.environ.get(
            f"{service.upper()}_DATABASE_URL", f"sqlite:///./data/{service}.db"
        )
    )


def database_identity(service: str) -> tuple[object, ...]:
    """Identify a database independently of credentials and driver spelling."""
    url = database_url(service)
    if url.get_backend_name() == "sqlite":
        path = Path(url.database or "")
        if not path.is_absolute():
            path = ROOT / "services" / service / path
        return ("sqlite", path.resolve())
    return (
        url.get_backend_name(),
        (url.host or "localhost").lower(),
        url.port or 5432,
        url.database,
    )


def reset_databases() -> None:
    """Validate distinct targets before destructively resetting either service."""
    if database_identity("game") == database_identity("auth"):
        raise ValueError("game and auth must use different databases")
    for service in ("game", "auth"):
        reset_database(service)


def reset_database(service: str) -> None:
    """Drop the configured service database and rebuild its migration head."""
    directory = ROOT / "services" / service
    url = database_url(service)
    if url.get_backend_name() == "sqlite":
        if not url.database or url.database == ":memory:":
            raise ValueError("db-reset requires a persistent SQLite database")
        path = Path(url.database)
        if not path.is_absolute():
            path = directory / path
        path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            Path(f"{path}{suffix}").unlink(missing_ok=True)
    elif url.get_backend_name() == "postgresql":
        database = url.database
        if not database or database in {"postgres", "template0", "template1"}:
            raise ValueError("db-reset requires a dedicated development database")
        engine = create_engine(
            url.set(database="postgres"), isolation_level="AUTOCOMMIT"
        )
        try:
            with engine.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :database AND pid <> pg_backend_pid()"
                    ),
                    {"database": database},
                )
                quoted = connection.dialect.identifier_preparer.quote_identifier(
                    database
                )
                connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {quoted}")
                connection.exec_driver_sql(f"CREATE DATABASE {quoted}")
        finally:
            engine.dispose()
    else:
        raise ValueError(f"Unsupported database backend: {url.get_backend_name()}")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=directory,
        check=True,
    )


if __name__ == "__main__":
    reset_databases()
