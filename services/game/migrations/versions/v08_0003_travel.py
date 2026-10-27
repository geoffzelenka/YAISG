"""Remove obsolete delayed relocation columns."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0003_travel"
down_revision = "v08_0002_presence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Journeys store step progress in active action metadata."""
    op.drop_column("estates", "relocating_to_realm_id")
    op.drop_column("estates", "relocation_completes_at")


def downgrade() -> None:
    """Restore the old disposable relocation fields."""
    op.add_column("estates", sa.Column("relocating_to_realm_id", sa.String(128)))
    op.add_column(
        "estates", sa.Column("relocation_completes_at", sa.DateTime(timezone=True))
    )
