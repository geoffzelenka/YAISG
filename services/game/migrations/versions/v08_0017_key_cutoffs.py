"""Retain historical key access and discovery lifecycle boundaries."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0017_key_cutoffs"
down_revision = "v08_0016_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Record access cutoffs and durable completed transition windows."""
    op.add_column(
        "item_instances",
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "realm_state",
        sa.Column("transition_history", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    """Remove historical boundaries from disposable state."""
    with op.batch_alter_table("realm_state") as batch:
        batch.drop_column("transition_history")
    with op.batch_alter_table("item_instances") as batch:
        batch.drop_column("invalidated_at")
