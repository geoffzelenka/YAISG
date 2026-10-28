"""The disposable v0.8 baseline works on either supported database."""

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.config import CONTENT_DIR
from app.content.runtime import CONTENT
from app.db import Base
from app.models import CharacterSkill


def _alembic(
    database_url: str, *arguments: str, content_dir: Path | None = None
) -> None:
    environment = {**os.environ, "GAME_DATABASE_URL": database_url}
    if content_dir is not None:
        environment["CONTENT_DIR"] = str(content_dir)
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env=environment,
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


def test_stance_migration_backfills_existing_characters(tmp_path: Path) -> None:
    """Upgrade populated v08_0014 using the selected content's default stance."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "progression.json"
    progression = json.loads(path.read_text())
    default = next(
        stance
        for stance in CONTENT.progression.stances
        if stance != CONTENT.progression.default_stance
    )
    progression["default_stance"] = default
    path.write_text(json.dumps(progression))
    url = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'stance.db'}")
    engine = sa.create_engine(url)
    try:
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        _alembic(url, "upgrade", "v08_0014_consumables_hp")
        metadata = sa.MetaData()
        players = sa.Table(
            "players",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("auth_user_id", sa.Uuid()),
            autoload_with=engine,
        )
        characters = sa.Table(
            "characters",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("player_id", sa.Uuid()),
            sa.Column("home_estate_id", sa.Uuid()),
            autoload_with=engine,
        )
        assert "stance" not in characters.c
        player_id, character_id = uuid.uuid4(), uuid.uuid4()
        with engine.begin() as connection:
            connection.execute(
                players.insert().values(
                    id=player_id,
                    auth_user_id=uuid.uuid4(),
                    created_at=datetime.now(UTC),
                )
            )
            connection.execute(
                characters.insert().values(
                    id=character_id,
                    player_id=player_id,
                    name="Existing Hero",
                    name_normalized="existing hero",
                    current_realm_id="placeholder",
                    home_estate_id=uuid.uuid4(),
                    created_at=datetime.now(UTC),
                    hp=47,
                )
            )
        _alembic(url, "upgrade", "head", content_dir=directory)
        upgraded = sa.Table("characters", sa.MetaData(), autoload_with=engine)
        with engine.connect() as connection:
            assert connection.execute(
                sa.select(upgraded.c.stance, upgraded.c.hp)
            ).one() == (default, 47)
        assert upgraded.c.stance.nullable is False
        _alembic(url, "check", content_dir=directory)
    finally:
        engine.dispose()
