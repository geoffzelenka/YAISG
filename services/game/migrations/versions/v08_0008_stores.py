"""Add realm stores, materialized demand lines and world seed marker."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0008_stores"
down_revision = "v08_0007_larder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create holdings and appetite tables."""
    op.create_table(
        "realm_stores",
        sa.Column(
            "realm_id",
            sa.String(128),
            sa.ForeignKey("realm_state.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("quantity_milli", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("quantity_milli >= 0", name="ck_realm_stores_nonnegative"),
    )
    op.create_table(
        "realm_lines",
        sa.Column(
            "realm_id",
            sa.String(128),
            sa.ForeignKey("realm_state.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("line_key", sa.String(512), primary_key=True),
        sa.Column("selector", sa.JSON(), nullable=False),
        sa.Column("value_measured", sa.Boolean(), nullable=False),
        *(
            sa.Column(name, sa.BigInteger(), nullable=False)
            for name in (
                "draw_per_day",
                "reserve",
                "cap",
                "stock",
                "in_transit",
                "budget_gold",
            )
        ),
    )
    op.create_table(
        "world_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seeded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_caravan_pass", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_version", sa.String(64), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_world_state_singleton"),
    )


def downgrade() -> None:
    """Remove world economy tables."""
    op.drop_table("world_state")
    op.drop_table("realm_lines")
    op.drop_table("realm_stores")
