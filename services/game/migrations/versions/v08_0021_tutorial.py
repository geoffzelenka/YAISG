"""Private tutorial progress and durable tutorial goods sinks."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0021_tutorial"
down_revision = "v08_0020_guests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add progress and once-only seed state."""
    with op.batch_alter_table("characters") as batch:
        batch.add_column(sa.Column("tutorial_step", sa.String(128)))
        batch.add_column(
            sa.Column(
                "tutorial_seeded",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    with op.batch_alter_table("goods_ledger") as batch:
        batch.drop_constraint("ck_goods_ledger_sink", type_="check")
        batch.create_check_constraint(
            "ck_goods_ledger_sink",
            "cause IN ('guest_purge', 'tutorial_destroy') AND amount_milli <= 0",
        )


def downgrade() -> None:
    """Remove tutorial state on disposable development data."""
    op.execute("DELETE FROM goods_ledger WHERE cause = 'tutorial_destroy'")
    with op.batch_alter_table("goods_ledger") as batch:
        batch.drop_constraint("ck_goods_ledger_sink", type_="check")
        batch.create_check_constraint(
            "ck_goods_ledger_sink", "cause = 'guest_purge' AND amount_milli <= 0"
        )
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("tutorial_seeded")
        batch.drop_column("tutorial_step")
