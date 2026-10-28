"""Operational counters and shared mutation limits."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0022_operations"
down_revision = "v08_0021_tutorial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable event deltas and bounded rate-window state."""
    op.create_table(
        "metric_deltas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_metric_deltas_name", "metric_deltas", ["name"])
    op.create_table(
        "mutation_windows",
        sa.Column("auth_user_id", sa.Uuid(), primary_key=True),
        sa.Column("window", sa.BigInteger(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )

    op.create_index("ix_mutation_windows_window", "mutation_windows", ["window"])


def downgrade() -> None:
    """Remove operational data."""
    op.drop_index("ix_mutation_windows_window", table_name="mutation_windows")
    op.drop_table("mutation_windows")
    op.drop_index("ix_metric_deltas_name", table_name="metric_deltas")
    op.drop_table("metric_deltas")
