"""The disposable v0.8 baseline works on either supported database."""

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.db import Base
from app.models import CharacterSkill


def _alembic(database_url: str, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "GAME_DATABASE_URL": database_url},
        check=True,
        capture_output=True,
        text=True,
    )


def test_v08_baseline_upgrade_check_and_downgrade(tmp_path: Path) -> None:
    """Head creates exactly the mapped schema and can rebuild from nothing."""
    url = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'migration.db'}")
    engine = sa.create_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    _alembic(url, "upgrade", "head")
    _alembic(url, "check")
    assert set(sa.inspect(engine).get_table_names()) == {
        *Base.metadata.tables,
        "alembic_version",
    }
    columns = sa.inspect(engine).get_columns("character_skills")
    assert isinstance(
        next(c for c in columns if c["name"] == "xp")["type"], sa.BigInteger
    )
    assert isinstance(CharacterSkill.__table__.c.xp.type, sa.BigInteger)
    with engine.begin() as connection:
        player_id, character_id = uuid.uuid4(), uuid.uuid4()
        connection.execute(
            Base.metadata.tables["players"]
            .insert()
            .values(
                id=player_id, auth_user_id=uuid.uuid4(), created_at=datetime.now(UTC)
            )
        )
        connection.execute(
            Base.metadata.tables["characters"]
            .insert()
            .values(
                id=character_id,
                player_id=player_id,
                name="Migration Hero",
                stance="placeholder",
                name_normalized="migration hero",
                current_realm_id="placeholder",
                home_estate_id=uuid.uuid4(),
                created_at=datetime.now(UTC),
            )
        )
        connection.execute(
            sa.insert(CharacterSkill).values(
                character_id=character_id, skill_id="placeholder", xp=2**40, level=100
            )
        )
        assert connection.scalar(sa.select(CharacterSkill.xp)) == 2**40
    _alembic(url, "downgrade", "base")
    assert sa.inspect(engine).get_table_names() == ["alembic_version"]
    _alembic(url, "upgrade", "head")
    engine.dispose()


def test_db_reset_rebuilds_both_services(tmp_path: Path) -> None:
    """Reset discards existing databases and leaves both migration heads usable."""
    root = Path(__file__).resolve().parents[3]
    game_url = f"sqlite:///{tmp_path / 'game.db'}"
    auth_url = f"sqlite:///{tmp_path / 'auth.db'}"
    environment = {
        **os.environ,
        "GAME_DATABASE_URL": game_url,
        "AUTH_DATABASE_URL": auth_url,
    }
    for _ in range(2):
        subprocess.run(
            [sys.executable, "scripts/db_reset.py"],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        for url, expected in ((game_url, "characters"), (auth_url, "users")):
            engine = sa.create_engine(url)
            assert sa.inspect(engine).has_table(expected)
            with engine.begin() as connection:
                assert not sa.inspect(connection).has_table("reset_marker")
                connection.exec_driver_sql("CREATE TABLE reset_marker (id INTEGER)")
            engine.dispose()
    _alembic(game_url, "upgrade", "head")


@pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
def test_db_reset_refuses_shared_database(tmp_path: Path, backend: str) -> None:
    """A shared target is rejected before either database is touched."""
    root = Path(__file__).resolve().parents[3]
    if backend == "sqlite":
        path = tmp_path / "shared.db"
        path.write_text("must survive")
        game_url = f"sqlite:///{path}"
        auth_url = f"sqlite:///{tmp_path / '.' / 'shared.db'}"
    else:
        game_url = "postgresql+psycopg://game:secret@localhost/shared"
        auth_url = "postgresql+psycopg://auth:other@LOCALHOST:5432/shared"
    result = subprocess.run(
        [sys.executable, "scripts/db_reset.py"],
        cwd=root,
        env={
            **os.environ,
            "GAME_DATABASE_URL": game_url,
            "AUTH_DATABASE_URL": auth_url,
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "game and auth must use different databases" in result.stderr
    if backend == "sqlite":
        assert path.read_text() == "must survive"
