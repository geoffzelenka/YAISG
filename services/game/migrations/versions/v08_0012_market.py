"""Add global market escrow slots and durable executions."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0012_market"
down_revision = "v08_0011_caravans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create slots and history with whole-unit holding constraints."""
    op.create_table(
        "market_orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "character_id", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("quantity_remaining", sa.BigInteger(), nullable=False),
        sa.Column("escrow_gold_remaining", sa.BigInteger(), nullable=False),
        sa.Column("fill_items", sa.BigInteger(), nullable=False),
        sa.Column("fill_gold", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "realm_id", sa.String(128), sa.ForeignKey("realm_state.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("side IN ('buy', 'sell')", name="ck_market_order_side"),
        sa.CheckConstraint(
            "status IN ('open', 'collectable', 'closed')", name="ck_market_order_status"
        ),
        sa.CheckConstraint(
            "unit_price > 0 AND quantity > 0 "
            "AND quantity_remaining >= 0 AND quantity_remaining <= quantity",
            name="ck_market_order_quantity",
        ),
        sa.CheckConstraint(
            "escrow_gold_remaining >= 0 AND fill_items >= 0 AND fill_gold >= 0",
            name="ck_market_order_holdings",
        ),
        sa.CheckConstraint(
            "(status = 'open' AND quantity_remaining > 0) OR "
            "(status <> 'open' AND quantity_remaining = 0 "
            "AND escrow_gold_remaining = 0)",
            name="ck_market_order_remainder",
        ),
        sa.CheckConstraint(
            "status <> 'closed' OR (fill_items = 0 AND fill_gold = 0 "
            "AND closed_at IS NOT NULL)",
            name="ck_market_order_closed",
        ),
    )
    op.create_index("ix_market_orders_character_id", "market_orders", ["character_id"])
    op.create_index(
        "ix_market_order_book",
        "market_orders",
        ["item_id", "side", "status", "unit_price", "created_at", "id"],
    )
    op.create_table(
        "market_matches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("maker_order_id", sa.Uuid(), nullable=False),
        sa.Column("taker_order_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_character_id", sa.Uuid(), nullable=False),
        sa.Column("seller_character_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("tax_gold", sa.BigInteger(), nullable=False),
        sa.Column("burned_gold", sa.BigInteger(), nullable=False),
        sa.Column("tax_realm_id", sa.String(128), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity > 0 AND unit_price > 0 AND tax_gold >= 0 "
            "AND burned_gold >= 0 AND burned_gold <= tax_gold "
            "AND tax_gold <= quantity * unit_price",
            name="ck_market_match_amounts",
        ),
    )
    for holder in ("buyer", "seller"):
        op.create_index(
            f"ix_market_matches_{holder}_character_id",
            "market_matches",
            [f"{holder}_character_id"],
        )


def downgrade() -> None:
    """Remove executions before slots."""
    op.drop_table("market_matches")
    op.drop_table("market_orders")
