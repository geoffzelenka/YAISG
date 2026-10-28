"""Add the standing combat stance."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0015_stance"
down_revision = "v08_0014_consumables_hp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the character setting."""
    op.add_column(
        "characters",
        sa.Column("stance", sa.String(128), nullable=False),
    )


def downgrade() -> None:
    """Remove the character setting."""
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("stance")
