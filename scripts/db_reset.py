"""Destructively recreate both development databases, then migrate to head."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def reset_database(service: str) -> None:
    """Drop the configured service database and rebuild its migration head."""
    directory = ROOT / "services" / service
    variable = f"{service.upper()}_DATABASE_URL"
    url = make_url(os.environ.get(variable, f"sqlite:///./data/{service}.db"))
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
    for service in ("game", "auth"):
        reset_database(service)
