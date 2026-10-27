"""Persist realm and estate decay stages for tag activation."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0001_tags"
down_revision = "v08_0000_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Initialize both holders as Fed."""
    with op.batch_alter_table("reward_log") as batch:
        batch.drop_constraint("ck_reward_log_cycles_positive", type_="check")
        batch.create_check_constraint("ck_reward_log_cycles_nonnegative", "cycles >= 0")
    for table in ("realm_state", "estates"):
        op.add_column(
            table,
            sa.Column(
                "decay_stage", sa.String(32), nullable=False, server_default="fed"
            ),
        )


def downgrade() -> None:
    """Remove stage state."""
    op.execute("DELETE FROM reward_log WHERE cycles = 0")
    with op.batch_alter_table("reward_log") as batch:
        batch.drop_constraint("ck_reward_log_cycles_nonnegative", type_="check")
        batch.create_check_constraint("ck_reward_log_cycles_positive", "cycles > 0")
    for table in ("estates", "realm_state"):
        op.drop_column(table, "decay_stage")
