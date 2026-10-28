"""Add permanent equipment holders."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0013_equipment"
down_revision = "v08_0012_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create concrete slots with positive quantities."""
    op.create_table(
        "character_equipment",
        sa.Column(
            "character_id",
            sa.Uuid(),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("slot", sa.String(16), primary_key=True),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0 AND (slot = 'utility' OR quantity = 1)",
            name="ck_equipment_quantity",
        ),
        sa.CheckConstraint(
            "slot IN ('head','chest','gloves','legs','feet','neck',"
            "'left_arm','right_arm','left_ring','right_ring','belt','cape',"
            "'right_hand','left_hand','utility')",
            name="ck_equipment_slot",
        ),
    )


def downgrade() -> None:
    """Remove equipment holders."""
    op.drop_table("character_equipment")
