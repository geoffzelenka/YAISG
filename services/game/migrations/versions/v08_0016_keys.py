"""Add instanced resource keys and private action references."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0016_keys"
down_revision = "v08_0015_stance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create nonfungible holdings and the nullable key action link."""
    op.create_table(
        "item_instances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("template_id", sa.String(128), nullable=False),
        sa.Column("holder_character_id", sa.Uuid(), sa.ForeignKey("characters.id")),
        sa.Column(
            "discovered_by_character_id",
            sa.Uuid(),
            sa.ForeignKey("characters.id", ondelete="SET NULL"),
        ),
        sa.Column("discovered_by_name", sa.String(20), nullable=False),
        sa.Column(
            "realm_id", sa.String(128), sa.ForeignKey("realm_state.id"), nullable=False
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("uses_total", sa.Integer(), nullable=False),
        sa.Column("uses_remaining", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "uses_total > 0 AND uses_remaining >= 0 AND uses_remaining <= uses_total",
            name="ck_instances_uses",
        ),
        sa.CheckConstraint(
            "state IN ('active', 'deprecated', 'invalid', 'depleted')",
            name="ck_instances_state",
        ),
    )
    op.create_index(
        "ix_item_instances_holder_character_id",
        "item_instances",
        ["holder_character_id"],
    )
    op.create_index("ix_item_instances_realm_id", "item_instances", ["realm_id"])
    with op.batch_alter_table("active_actions") as batch:
        batch.add_column(sa.Column("key_instance_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_active_actions_key", "item_instances", ["key_instance_id"], ["id"]
        )


def downgrade() -> None:
    """Remove private action references before instance holdings."""
    with op.batch_alter_table("active_actions") as batch:
        batch.drop_constraint("fk_active_actions_key", type_="foreignkey")
        batch.drop_column("key_instance_id")
    op.drop_table("item_instances")
