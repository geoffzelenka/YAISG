"""Project attempts, consumed contribution credits, and global kickoff limit."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0005_projects"
down_revision = "v08_0004_graph"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project lifecycle tables and link acquired tags to attempts."""
    op.add_column(
        "characters", sa.Column("last_kickoff_at", sa.DateTime(timezone=True))
    )
    op.create_table(
        "realm_project_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "realm_id", sa.String(128), sa.ForeignKey("realm_state.id"), nullable=False
        ),
        sa.Column("project_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "kicked_off_by", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("kicked_off_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("required", sa.JSON(), nullable=False),
        sa.Column("contributed", sa.JSON(), nullable=False),
        sa.Column("last_contribution_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("build_completes_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('funding', 'building', 'complete', 'failed')",
            name="ck_project_run_status",
        ),
    )
    op.create_index(
        "uq_realm_active_project",
        "realm_project_runs",
        ["realm_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('funding', 'building')"),
        postgresql_where=sa.text("status IN ('funding', 'building')"),
    )
    op.create_table(
        "realm_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id", sa.Uuid(), sa.ForeignKey("realm_project_runs.id"), nullable=False
        ),
        sa.Column("character_id", sa.Uuid(), sa.ForeignKey("characters.id")),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("quantity_milli", sa.BigInteger(), nullable=False),
        sa.Column("contributed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_milli > 0", name="ck_contribution_positive"),
    )
    op.create_index("ix_realm_contributions_run_id", "realm_contributions", ["run_id"])
    with op.batch_alter_table("realm_tags") as batch:
        batch.create_foreign_key(
            "fk_realm_tags_project_run",
            "realm_project_runs",
            ["project_run_id"],
            ["id"],
        )


def downgrade() -> None:
    """Remove project attempts after removing the tag references."""
    with op.batch_alter_table("realm_tags") as batch:
        batch.drop_constraint("fk_realm_tags_project_run", type_="foreignkey")
    op.drop_table("realm_contributions")
    op.drop_table("realm_project_runs")
    op.drop_column("characters", "last_kickoff_at")
