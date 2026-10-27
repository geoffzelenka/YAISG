"""Add deposit-only estate larders."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0007_larder"
down_revision = "v08_0006_estates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create larder holdings in milli-units."""
    op.create_table(
        "estate_larder",
        sa.Column(
            "estate_id",
            sa.Uuid(),
            sa.ForeignKey("estates.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("quantity_milli", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("quantity_milli > 0", name="ck_estate_larder_positive"),
    )


def downgrade() -> None:
    """Remove larder holdings."""
    op.drop_table("estate_larder")
