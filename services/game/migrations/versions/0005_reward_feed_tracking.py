"""Add durable reward-feed claim tracking.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store complete feed details and whether each reward was returned."""
    with op.batch_alter_table("reward_log") as batch_op:
        batch_op.add_column(
            sa.Column("details", sa.JSON(), nullable=False, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Remove reward-feed claim tracking."""
    with op.batch_alter_table("reward_log") as batch_op:
        batch_op.drop_column("claimed_at")
        batch_op.drop_column("details")
