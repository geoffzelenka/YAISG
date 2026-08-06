"""Migrate realm and estate persistence to the v0.5 graph model.

Revision ID: 0006
Revises: 0005
"""

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STARTING_NODES = {
    "realm.verdant_vale": "node.verdant_t1",
    "realm.ashen_reach": "node.ashen_t1",
}
# Migrations must remain runnable after content changes, so the v0.5 backfill
# snapshot is intentionally embedded rather than loading mutable pack files.


def _uuid(value: uuid.UUID | str) -> uuid.UUID:
    """Normalize UUID values returned as strings by SQLite text queries."""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


def _datetime(value: datetime | str | None, fallback: datetime) -> datetime:
    """Normalize timestamps returned as strings by SQLite text queries."""
    if value is None:
        return fallback
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def _json(value: object) -> object:
    """Normalize JSON returned as text by SQLite migration queries."""
    return json.loads(value) if isinstance(value, str) else value


def upgrade() -> None:
    """Install v0.5 structures and backfill existing ownership/residence."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    estate_owner_unique = next(
        (
            constraint["name"]
            for constraint in inspector.get_unique_constraints("estates")
            if constraint["column_names"] == ["character_id"]
        ),
        None,
    )
    constraint_name = estate_owner_unique or "uq_estates_character_id"
    with op.batch_alter_table("estates", naming_convention=naming) as batch:
        batch.alter_column(
            "character_id", new_column_name="owner_character_id", nullable=True
        )
        batch.add_column(sa.Column("form_id", sa.String(128), nullable=True))
        batch.add_column(
            sa.Column("status", sa.String(32), nullable=False, server_default="active")
        )
        batch.add_column(
            sa.Column("relocating_to_realm_id", sa.String(128), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "relocation_completes_at", sa.DateTime(timezone=True), nullable=True
            )
        )
        batch.drop_constraint(constraint_name, type_="unique")
    connection.execute(sa.text("UPDATE estates SET form_id = 'form.homestead'"))
    with op.batch_alter_table("estates", naming_convention=naming) as batch:
        batch.alter_column("form_id", nullable=False)
    op.create_index(
        "uq_estates_active_owner",
        "estates",
        ["owner_character_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    with op.batch_alter_table("characters") as batch:
        batch.add_column(sa.Column("home_estate_id", sa.Uuid(), nullable=True))
    connection.execute(
        sa.text(
            "UPDATE characters SET home_estate_id = "
            "(SELECT estates.id FROM estates WHERE "
            "estates.owner_character_id = characters.id "
            "AND estates.status = 'active')"
        )
    )
    with op.batch_alter_table("characters") as batch:
        batch.alter_column("home_estate_id", nullable=False)

    op.create_table(
        "estate_ownership_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "estate_id",
            sa.Uuid(),
            sa.ForeignKey("estates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "character_id", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relinquished_at", sa.DateTime(timezone=True), nullable=True),
    )
    now = datetime.now(UTC)
    rows = connection.execute(
        sa.text(
            "SELECT e.id, e.owner_character_id, c.created_at FROM estates e "
            "JOIN characters c ON c.id = e.owner_character_id"
        )
    ).mappings()
    history = sa.table(
        "estate_ownership_history",
        sa.column("id", sa.Uuid()),
        sa.column("estate_id", sa.Uuid()),
        sa.column("character_id", sa.Uuid()),
        sa.column("acquired_at", sa.DateTime(timezone=True)),
        sa.column("relinquished_at", sa.DateTime(timezone=True)),
    )
    for row in rows:
        connection.execute(
            history.insert().values(
                id=uuid.uuid4(),
                estate_id=_uuid(row["id"]),
                character_id=_uuid(row["owner_character_id"]),
                acquired_at=_datetime(row["created_at"], now),
                relinquished_at=None,
            )
        )

    legacy_realm_state = inspector.has_table("realm_state")
    legacy_contributions = inspector.has_table("realm_contributions")
    legacy_projects: dict[str, tuple[str, object]] = {}
    if legacy_realm_state:
        legacy_projects = {
            row["realm_id"]: (row["project_id"], row["contribution_totals"])
            for row in connection.execute(
                sa.text(
                    "SELECT realm_id, project_id, contribution_totals FROM realm_state"
                )
            ).mappings()
        }
    if legacy_contributions:
        with op.batch_alter_table("realm_contributions") as batch:
            batch.add_column(sa.Column("project_id", sa.String(128), nullable=True))
        for realm_id, (project_id, _) in legacy_projects.items():
            connection.execute(
                sa.text(
                    "UPDATE realm_contributions SET project_id = :project_id "
                    "WHERE realm_id = :realm_id"
                ),
                {"project_id": project_id, "realm_id": realm_id},
            )
        with op.batch_alter_table("realm_contributions") as batch:
            batch.alter_column("project_id", nullable=False)
    else:
        op.create_table(
            "realm_contributions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("realm_id", sa.String(128), nullable=False),
            sa.Column("project_id", sa.String(128), nullable=False),
            sa.Column(
                "character_id",
                sa.Uuid(),
                sa.ForeignKey("characters.id"),
                nullable=False,
            ),
            sa.Column("item_id", sa.String(128), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("contributed_at", sa.DateTime(timezone=True), nullable=False),
        )

    if legacy_realm_state:
        with op.batch_alter_table("realm_state") as batch:
            batch.add_column(sa.Column("node_id", sa.String(128), nullable=True))
            batch.add_column(sa.Column("transition_to_node_id", sa.String(128)))
            batch.add_column(
                sa.Column("transition_completes_at", sa.DateTime(timezone=True))
            )
            batch.add_column(
                sa.Column("treasury", sa.Integer(), nullable=False, server_default="0")
            )
        for realm_id in legacy_projects:
            node_id = STARTING_NODES.get(realm_id)
            if node_id is None:
                raise RuntimeError(f"cannot backfill unknown realm {realm_id!r}")
            connection.execute(
                sa.text(
                    "UPDATE realm_state SET node_id = :node_id "
                    "WHERE realm_id = :realm_id"
                ),
                {"node_id": node_id, "realm_id": realm_id},
            )
        with op.batch_alter_table("realm_state") as batch:
            batch.alter_column("node_id", nullable=False)
            batch.drop_column("tier")
            batch.drop_column("project_id")
            batch.drop_column("contribution_totals")
    else:
        op.create_table(
            "realm_state",
            sa.Column("realm_id", sa.String(128), primary_key=True),
            sa.Column("node_id", sa.String(128), nullable=False),
            sa.Column("transition_to_node_id", sa.String(128), nullable=True),
            sa.Column(
                "transition_completes_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("treasury", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        )
    realm_state = sa.table(
        "realm_state",
        sa.column("realm_id", sa.String()),
        sa.column("node_id", sa.String()),
        sa.column("treasury", sa.Integer()),
        sa.column("data", sa.JSON()),
    )
    realm_ids = set(STARTING_NODES) | {
        row[0]
        for row in connection.execute(
            sa.text("SELECT DISTINCT realm_id FROM characters")
        )
    }
    existing_realm_ids = set(legacy_projects)
    for realm_id in realm_ids - existing_realm_ids:
        node_id = STARTING_NODES.get(realm_id)
        if node_id is None:
            raise RuntimeError(f"cannot backfill unknown realm {realm_id!r}")
        connection.execute(
            realm_state.insert().values(
                realm_id=realm_id, node_id=node_id, treasury=0, data={}
            )
        )
    op.create_table(
        "realm_edge_progress",
        sa.Column("realm_id", sa.String(128), primary_key=True),
        sa.Column("edge_id", sa.String(128), primary_key=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "realm_projects",
        sa.Column("realm_id", sa.String(128), primary_key=True),
        sa.Column("project_id", sa.String(128), primary_key=True),
        sa.Column(
            "contribution_totals", sa.JSON(), nullable=False, server_default="{}"
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    realm_projects = sa.table(
        "realm_projects",
        sa.column("realm_id", sa.String()),
        sa.column("project_id", sa.String()),
        sa.column("contribution_totals", sa.JSON()),
        sa.column("status", sa.String()),
    )
    for realm_id, (project_id, totals) in legacy_projects.items():
        connection.execute(
            realm_projects.insert().values(
                realm_id=realm_id,
                project_id=project_id,
                contribution_totals=_json(totals),
                status="active",
            )
        )


def downgrade() -> None:
    """Restore the Phase 3 estate shape and drop graph state cleanly."""
    for table in (
        "realm_contributions",
        "realm_projects",
        "realm_edge_progress",
        "realm_state",
        "estate_ownership_history",
    ):
        op.drop_table(table)
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("home_estate_id")
    op.drop_index("uq_estates_active_owner", table_name="estates")
    with op.batch_alter_table("estates") as batch:
        batch.create_unique_constraint(
            "uq_estates_character_id", ["owner_character_id"]
        )
        batch.alter_column(
            "owner_character_id", new_column_name="character_id", nullable=False
        )
        batch.drop_column("relocation_completes_at")
        batch.drop_column("relocating_to_realm_id")
        batch.drop_column("status")
        batch.drop_column("form_id")
