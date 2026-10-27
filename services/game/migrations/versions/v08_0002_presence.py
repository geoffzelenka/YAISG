"""Rename character location to current realm.

Revision ID: v08_0002_presence
Revises: v08_0001_tags
"""

from alembic import op

revision = "v08_0002_presence"
down_revision = "v08_0001_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Keep estate home location distinct from character presence."""
    op.alter_column("characters", "realm_id", new_column_name="current_realm_id")


def downgrade() -> None:
    """Restore the previous character location name."""
    op.alter_column("characters", "current_realm_id", new_column_name="realm_id")
