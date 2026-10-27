"""Replace estate counters with form-owned capacity and decay state."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0006_estates"
down_revision = "v08_0005_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add decay counters and remove obsolete estate counters."""
    with op.batch_alter_table("estates") as batch:
        batch.drop_column("level")
        batch.drop_column("upgrade_slots")
        batch.add_column(
            sa.Column("gauge", sa.Float(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("shed_progress", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    """Restore the previous disposable estate shape."""
    with op.batch_alter_table("estates") as batch:
        batch.drop_column("gauge")
        batch.drop_column("shed_progress")
        batch.add_column(
            sa.Column("level", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(
            sa.Column("upgrade_slots", sa.Integer(), nullable=False, server_default="0")
        )
