"""Create character profile tables.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create character, progression, currency, estate, and inventory tables."""
    op.create_table(
        "characters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("name_normalized", sa.String(length=20), nullable=False),
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_normalized"),
        sa.UniqueConstraint("player_id"),
    )
    op.create_table(
        "character_skills",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.CheckConstraint("level >= 1", name="ck_character_skills_level_positive"),
        sa.CheckConstraint("xp >= 0", name="ck_character_skills_xp_nonnegative"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("character_id", "skill_id"),
    )
    op.create_table(
        "currency",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("gold", sa.Integer(), nullable=False),
        sa.Column("premium", sa.Integer(), nullable=False),
        sa.CheckConstraint("gold >= 0", name="ck_currency_gold_nonnegative"),
        sa.CheckConstraint("premium >= 0", name="ck_currency_premium_nonnegative"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("character_id"),
    )
    op.create_table(
        "estates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("upgrade_slots", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id"),
    )
    op.create_table(
        "estate_upgrades",
        sa.Column("estate_id", sa.Uuid(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("upgrade_id", sa.String(length=128), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["estate_id"], ["estates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("estate_id", "slot_index"),
    )
    op.create_table(
        "inventories",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_inventories_quantity_positive"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("character_id", "item_id"),
    )


def downgrade() -> None:
    """Drop character profile tables in dependency order."""
    for table in (
        "inventories",
        "estate_upgrades",
        "estates",
        "currency",
        "character_skills",
        "characters",
    ):
        op.drop_table(table)
