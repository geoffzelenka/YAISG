"""Add the signed gold ledger and widen player wallets."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0009_gold"
down_revision = "v08_0008_stores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable audit entries and 64-bit wallets."""
    op.create_table(
        "gold_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cause", sa.String(32), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("realm_id", sa.String(128), nullable=True),
        sa.Column("character_id", sa.Uuid(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "cause IN ('world_seed', 'mint', 'tutorial_seed', "
            "'tutorial_destroy', 'tax_burn', 'caravan_fee_burn')",
            name="ck_gold_ledger_cause",
        ),
        sa.CheckConstraint(
            "(cause IN ('world_seed', 'mint', 'tutorial_seed') AND amount >= 0) OR "
            "(cause IN ('tutorial_destroy', 'tax_burn', "
            "'caravan_fee_burn') AND amount <= 0)",
            name="ck_gold_ledger_sign",
        ),
    )
    with op.batch_alter_table("currency") as batch:
        batch.alter_column(
            "gold",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Remove audit entries and restore the previous wallet type."""
    with op.batch_alter_table("currency") as batch:
        batch.alter_column(
            "gold",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
    op.drop_table("gold_ledger")
