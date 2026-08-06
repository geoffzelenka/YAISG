"""Alembic migration tests for the v0.5 realm and estate reshape."""

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa


def _alembic(database_url: str, revision: str, direction: str = "upgrade") -> None:
    environment = {**os.environ, "GAME_DATABASE_URL": database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", direction, revision],
        cwd=Path(__file__).parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_v05_backfills_phase3_data_and_downgrades(tmp_path: Path) -> None:
    """A populated Phase 3 database upgrades with every required backfill."""
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    _alembic(database_url, "0005")
    engine = sa.create_engine(database_url)
    player_id = uuid.uuid4()
    character_id = uuid.uuid4()
    estate_id = uuid.uuid4()
    contribution_id = uuid.uuid4()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO players (id, auth_user_id, created_at) "
                "VALUES (:id, :auth_user_id, :created_at)"
            ),
            {
                "id": player_id.hex,
                "auth_user_id": uuid.uuid4().hex,
                "created_at": created_at,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO characters "
                "(id, player_id, name, name_normalized, realm_id, created_at) "
                "VALUES (:id, :player_id, 'Hero', 'hero', :realm_id, :created_at)"
            ),
            {
                "id": character_id.hex,
                "player_id": player_id.hex,
                "realm_id": "realm.verdant_vale",
                "created_at": created_at,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO estates "
                "(id, character_id, realm_id, level, upgrade_slots, data) "
                "VALUES (:id, :character_id, :realm_id, 1, 2, '{}')"
            ),
            {
                "id": estate_id.hex,
                "character_id": character_id.hex,
                "realm_id": "realm.verdant_vale",
            },
        )
        connection.execute(
            sa.text(
                "CREATE TABLE realm_state ("
                "realm_id VARCHAR(128) PRIMARY KEY, tier INTEGER NOT NULL, "
                "project_id VARCHAR(128) NOT NULL, "
                "contribution_totals JSON NOT NULL, data JSON NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO realm_state VALUES ('realm.verdant_vale', 0, "
                "'project.verdant_cardboard', '{\"item.demo_crate\": 4}', '{}')"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE realm_contributions ("
                "id CHAR(32) PRIMARY KEY, realm_id VARCHAR(128) NOT NULL, "
                "character_id CHAR(32) NOT NULL, "
                "item_id VARCHAR(128) NOT NULL, quantity INTEGER NOT NULL, "
                "contributed_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO realm_contributions VALUES (:id, 'realm.verdant_vale', "
                ":character_id, 'item.demo_crate', 4, :contributed_at)"
            ),
            {
                "id": contribution_id.hex,
                "character_id": character_id.hex,
                "contributed_at": created_at,
            },
        )

    _alembic(database_url, "0006")
    with engine.connect() as connection:
        estate = connection.execute(
            sa.text("SELECT owner_character_id, form_id, status FROM estates")
        ).one()
        character = connection.execute(
            sa.text("SELECT home_estate_id FROM characters")
        ).scalar_one()
        history = connection.execute(
            sa.text("SELECT estate_id, character_id FROM estate_ownership_history")
        ).one()
        realm = connection.execute(
            sa.text(
                "SELECT node_id FROM realm_state WHERE realm_id = 'realm.verdant_vale'"
            )
        ).scalar_one()
        project_id = connection.execute(
            sa.text("SELECT project_id FROM realm_contributions")
        ).scalar_one()
        project_totals = connection.execute(
            sa.text("SELECT contribution_totals FROM realm_projects")
        ).scalar_one()
    assert estate == (character_id.hex, "form.homestead", "active")
    assert character == estate_id.hex
    assert history == (estate_id.hex, character_id.hex)
    assert realm == "node.verdant_t1"
    assert project_id == "project.verdant_cardboard"
    assert '"item.demo_crate": 4' in project_totals

    _alembic(database_url, "0005", "downgrade")
    inspector = sa.inspect(engine)
    assert "character_id" in {
        column["name"] for column in inspector.get_columns("estates")
    }
    assert not inspector.has_table("realm_state")
    engine.dispose()
