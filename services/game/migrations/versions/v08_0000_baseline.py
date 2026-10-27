"""baseline

Revision ID: v08_0000_baseline
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v08_0000_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the complete disposable game baseline."""
    op.create_table(
        "players",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auth_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_user_id"),
    )
    op.create_table(
        "realm_edge_progress",
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("edge_id", sa.String(length=128), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("realm_id", "edge_id"),
    )
    op.create_table(
        "realm_projects",
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("contribution_totals", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("realm_id", "project_id"),
    )
    op.create_table(
        "realm_state",
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("transition_to_node_id", sa.String(length=128), nullable=True),
        sa.Column("transition_completes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("realm_id"),
    )
    op.create_table(
        "characters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("name_normalized", sa.String(length=20), nullable=False),
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("home_estate_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_normalized"),
        sa.UniqueConstraint("player_id"),
    )
    op.create_table(
        "active_actions",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("character_id"),
    )
    op.create_table(
        "character_skills",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("xp", sa.BigInteger(), nullable=False),
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
        sa.Column("owner_character_id", sa.Uuid(), nullable=True),
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("form_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("relocating_to_realm_id", sa.String(length=128), nullable=True),
        sa.Column("relocation_completes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("upgrade_slots", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_character_id"], ["characters.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
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
    op.create_table(
        "realm_contributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("realm_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("contributed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reward_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("cycles", sa.Integer(), nullable=False),
        sa.Column("xp", sa.JSON(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("cycles > 0", name="ck_reward_log_cycles_positive"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reward_log_character_id"), "reward_log", ["character_id"], unique=False
    )
    op.create_table(
        "estate_ownership_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("estate_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relinquished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
        ),
        sa.ForeignKeyConstraint(["estate_id"], ["estates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
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


def downgrade() -> None:
    """Remove all game baseline tables."""
    op.drop_table("estate_upgrades")
    op.drop_table("estate_ownership_history")
    op.drop_index(op.f("ix_reward_log_character_id"), table_name="reward_log")
    op.drop_table("reward_log")
    op.drop_table("realm_contributions")
    op.drop_table("inventories")
    op.drop_table("estates")
    op.drop_table("currency")
    op.drop_table("character_skills")
    op.drop_table("active_actions")
    op.drop_table("characters")
    op.drop_table("realm_state")
    op.drop_table("realm_projects")
    op.drop_table("realm_edge_progress")
    op.drop_table("players")
