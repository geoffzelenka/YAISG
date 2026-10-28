"""Index open key listings and seller capacity checks."""

from alembic import op

revision = "v08_0019_key_listing_indexes"
down_revision = "v08_0018_key_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes without changing the unique physical-custody constraint."""
    op.create_index(
        "ix_key_listings_seller_status",
        "key_listings",
        ["seller_character_id", "status"],
    )
    op.create_index("ix_key_listings_status", "key_listings", ["status"])


def downgrade() -> None:
    """Remove listing lookup indexes."""
    op.drop_index("ix_key_listings_status", table_name="key_listings")
    op.drop_index("ix_key_listings_seller_status", table_name="key_listings")
