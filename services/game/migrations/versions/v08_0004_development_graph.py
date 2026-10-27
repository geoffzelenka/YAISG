"""Replace disposable edge/project state with realm instances and tag stacks."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0004_graph"
down_revision = "v08_0003_travel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rebuild realm state without preserving development data."""
    op.drop_table("realm_contributions")
    op.drop_table("realm_projects")
    op.drop_table("realm_edge_progress")
    op.drop_table("realm_state")
    op.create_table(
        "realm_state",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("template_id", sa.String(128), nullable=False),
        sa.Column("isolated", sa.Boolean(), nullable=False),
        sa.Column("owner_character_id", sa.Uuid(), sa.ForeignKey("characters.id")),
        sa.Column("current_node_id", sa.String(128), nullable=False),
        sa.Column("treasury", sa.BigInteger(), nullable=False),
        sa.Column("pending_transition", sa.JSON()),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gauge", sa.Float(), nullable=False),
        sa.Column("decay_stage", sa.String(32), nullable=False, server_default="fed"),
        sa.Column("shed_progress", sa.Float(), nullable=False),
        sa.Column("vote_cooldown_until", sa.DateTime(timezone=True)),
        sa.Column("treasury_band", sa.String(32)),
        sa.Column("tag_seq", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "realm_tags",
        sa.Column(
            "realm_id",
            sa.String(128),
            sa.ForeignKey("realm_state.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("tag_id", sa.String(128), primary_key=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("node_id", sa.String(128), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_run_id", sa.Uuid()),
        sa.UniqueConstraint("realm_id", "seq", name="uq_realm_tags_seq"),
        sa.CheckConstraint("seq > 0", name="ck_realm_tags_seq_positive"),
    )


def downgrade() -> None:
    """Restore the previous disposable realm schema."""
    op.drop_table("realm_tags")
    op.drop_table("realm_state")
    op.create_table(
        "realm_state",
        sa.Column("realm_id", sa.String(128), primary_key=True),
        sa.Column("node_id", sa.String(128), nullable=False),
        sa.Column("transition_to_node_id", sa.String(128)),
        sa.Column("transition_completes_at", sa.DateTime(timezone=True)),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("decay_stage", sa.String(32), nullable=False, server_default="fed"),
    )
    op.create_table(
        "realm_edge_progress",
        sa.Column("realm_id", sa.String(128), primary_key=True),
        sa.Column("edge_id", sa.String(128), primary_key=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "realm_projects",
        sa.Column("realm_id", sa.String(128), primary_key=True),
        sa.Column("project_id", sa.String(128), primary_key=True),
        sa.Column("contribution_totals", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "realm_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("realm_id", sa.String(128), nullable=False),
        sa.Column("project_id", sa.String(128), nullable=False),
        sa.Column(
            "character_id", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("contributed_at", sa.DateTime(timezone=True), nullable=False),
    )
