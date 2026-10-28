"""Guest activity, deletion-safe provenance and durable purge accounting."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0020_guests"
down_revision = "v08_0019_key_listing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add guest retention and signed audit sinks."""
    with op.batch_alter_table("players") as batch:
        batch.add_column(
            sa.Column("kind", sa.String(16), nullable=False, server_default="full")
        )
        batch.add_column(sa.Column("last_activity_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("session_expires_at", sa.DateTime(timezone=True)))
        batch.create_check_constraint("ck_players_kind", "kind IN ('guest', 'full')")
    for table, column in (
        ("realm_project_runs", "kicked_off_by"),
        ("realm_votes", "called_by"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.alter_column(column, existing_type=sa.Uuid(), nullable=True)
    with op.batch_alter_table("gold_ledger") as batch:
        batch.drop_constraint("ck_gold_ledger_cause", type_="check")
        batch.drop_constraint("ck_gold_ledger_sign", type_="check")
        batch.create_check_constraint(
            "ck_gold_ledger_cause",
            "cause IN ('world_seed', 'mint', 'tutorial_seed', 'tutorial_destroy', "
            "'tax_burn', 'caravan_fee_burn', 'guest_purge')",
        )
        batch.create_check_constraint(
            "ck_gold_ledger_sign",
            "(cause IN ('world_seed', 'mint', "
            "'tutorial_seed') AND amount >= 0) OR (cause IN ('tutorial_destroy', "
            "'tax_burn', 'caravan_fee_burn', 'guest_purge') AND amount <= 0)",
        )
    op.create_table(
        "goods_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cause", sa.String(32), nullable=False),
        sa.Column("item_id", sa.String(256), nullable=False),
        sa.Column("amount_milli", sa.BigInteger(), nullable=False),
        sa.Column("holder", sa.String(256), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "cause = 'guest_purge' AND amount_milli <= 0", name="ck_goods_ledger_sink"
        ),
    )


def downgrade() -> None:
    """Revert disposable guest support."""
    op.drop_table("goods_ledger")
    op.execute("DELETE FROM gold_ledger WHERE cause = 'guest_purge'")
    with op.batch_alter_table("gold_ledger") as batch:
        batch.drop_constraint("ck_gold_ledger_cause", type_="check")
        batch.drop_constraint("ck_gold_ledger_sign", type_="check")
        batch.create_check_constraint(
            "ck_gold_ledger_cause",
            "cause IN ('world_seed', 'mint', 'tutorial_seed', 'tutorial_destroy', "
            "'tax_burn', 'caravan_fee_burn')",
        )
        batch.create_check_constraint(
            "ck_gold_ledger_sign",
            "(cause IN ('world_seed', 'mint', "
            "'tutorial_seed') AND amount >= 0) OR (cause IN ('tutorial_destroy', "
            "'tax_burn', 'caravan_fee_burn') AND amount <= 0)",
        )
    # Development data is disposable; remove anonymous history before NOT NULL.
    op.execute(
        "DELETE FROM realm_tags WHERE project_run_id IN "
        "(SELECT id FROM realm_project_runs WHERE kicked_off_by IS NULL)"
    )
    op.execute(
        "DELETE FROM realm_contributions WHERE run_id IN "
        "(SELECT id FROM realm_project_runs WHERE kicked_off_by IS NULL)"
    )
    op.execute("DELETE FROM realm_project_runs WHERE kicked_off_by IS NULL")
    op.execute(
        "DELETE FROM realm_vote_eligibility WHERE vote_id IN "
        "(SELECT id FROM realm_votes WHERE called_by IS NULL)"
    )
    op.execute("DELETE FROM realm_votes WHERE called_by IS NULL")
    for table, column in (
        ("realm_project_runs", "kicked_off_by"),
        ("realm_votes", "called_by"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.alter_column(column, existing_type=sa.Uuid(), nullable=False)
    with op.batch_alter_table("players") as batch:
        batch.drop_constraint("ck_players_kind", type_="check")
        batch.drop_column("session_expires_at")
        batch.drop_column("last_activity_at")
        batch.drop_column("kind")
