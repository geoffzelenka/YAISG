"""Add belt stacks, timed buffs and lazy hit points."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0014_consumables_hp"
down_revision = "v08_0013_equipment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create consumable holders and timestamped health."""
    op.add_column(
        "characters", sa.Column("hp", sa.Float(), nullable=False, server_default="0")
    )
    op.add_column(
        "characters",
        sa.Column("hp_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "character_belt",
        sa.Column(
            "character_id",
            sa.Uuid(),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("slot", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.JSON(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_belt_quantity"),
        sa.CheckConstraint("slot >= 0", name="ck_belt_slot"),
    )
    op.create_table(
        "character_buffs",
        sa.Column(
            "character_id",
            sa.Uuid(),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Remove health and consumable holders."""
    op.drop_table("character_buffs")
    op.drop_table("character_belt")
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("hp_updated_at")
        batch.drop_column("hp")
