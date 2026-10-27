"""Add durable caravan shipments."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0011_caravans"
down_revision = "v08_0010_votes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create shipment holdings and audit trail."""
    op.create_table(
        "realm_shipments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "from_realm_id",
            sa.String(128),
            sa.ForeignKey("realm_state.id"),
            nullable=False,
        ),
        sa.Column(
            "to_realm_id",
            sa.String(128),
            sa.ForeignKey("realm_state.id"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("quantity_sent", sa.BigInteger(), nullable=False),
        sa.Column("quantity_arriving", sa.BigInteger(), nullable=False),
        sa.Column("goods_gold", sa.BigInteger(), nullable=False),
        sa.Column("fee_gold", sa.BigInteger(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrives_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "quantity_sent > 0 AND quantity_arriving >= 0 "
            "AND quantity_arriving <= quantity_sent",
            name="ck_shipment_goods",
        ),
        sa.CheckConstraint(
            "goods_gold >= 0 AND fee_gold >= 0", name="ck_shipment_gold"
        ),
        sa.CheckConstraint(
            "status IN ('in_transit', 'arrived')", name="ck_shipment_status"
        ),
    )
    op.create_index(
        "ix_realm_shipments_to_realm_id", "realm_shipments", ["to_realm_id"]
    )


def downgrade() -> None:
    """Remove shipment holdings."""
    op.drop_index("ix_realm_shipments_to_realm_id", table_name="realm_shipments")
    op.drop_table("realm_shipments")
