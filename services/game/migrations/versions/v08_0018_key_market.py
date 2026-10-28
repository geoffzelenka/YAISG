"""Add fixed-price key custody."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0018_key_market"
down_revision = "v08_0017_key_cutoffs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create listings on the disposable development schema."""
    op.create_table(
        "key_listings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "instance_id",
            sa.Uuid(),
            sa.ForeignKey("item_instances.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "seller_character_id",
            sa.Uuid(),
            sa.ForeignKey("characters.id"),
            nullable=False,
        ),
        sa.Column("price_gold", sa.BigInteger(), nullable=False),
        sa.Column(
            "realm_id", sa.String(128), sa.ForeignKey("realm_state.id"), nullable=False
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True)),
        sa.Column("buyer_character_id", sa.Uuid(), sa.ForeignKey("characters.id")),
        sa.CheckConstraint("price_gold > 0", name="ck_key_listing_price"),
        sa.CheckConstraint(
            "status IN ('open', 'sold', 'cancelled')", name="ck_key_listing_status"
        ),
    )


def downgrade() -> None:
    """Remove listing custody."""
    op.drop_table("key_listings")
