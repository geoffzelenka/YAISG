"""Remove the unused mutation-window pruning index."""

from alembic import op

revision = "v08_0023_conformance"
down_revision = "v08_0022_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Request upserts use the primary key; no pruning job consumes this index."""
    op.drop_index("ix_mutation_windows_window", table_name="mutation_windows")


def downgrade() -> None:
    """Restore the former operational index."""
    op.create_index("ix_mutation_windows_window", "mutation_windows", ["window"])
