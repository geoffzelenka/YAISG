"""Add active action state and resolution reward history.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create action state and reward history tables."""
    op.create_table(
        "active_actions",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("character_id"),
    )
    op.create_table(
        "reward_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("cycles", sa.Integer(), nullable=False),
        sa.Column("xp", sa.JSON(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("cycles > 0", name="ck_reward_log_cycles_positive"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reward_log_character_id"), "reward_log", ["character_id"])


def downgrade() -> None:
    """Remove reward history and active action state."""
    op.drop_index(op.f("ix_reward_log_character_id"), table_name="reward_log")
    op.drop_table("reward_log")
    op.drop_table("active_actions")
