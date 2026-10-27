"""Add aggregate secret ballots and eligibility snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "v08_0010_votes"
down_revision = "v08_0009_gold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ballots without any per-character choice storage."""
    op.create_table(
        "realm_votes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "realm_id", sa.String(128), sa.ForeignKey("realm_state.id"), nullable=False
        ),
        sa.Column("upgrade_id", sa.String(128), nullable=False),
        sa.Column(
            "called_by", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("yes_weight", sa.BigInteger(), nullable=False),
        sa.Column("no_weight", sa.BigInteger(), nullable=False),
        sa.Column("eligible_weight", sa.BigInteger(), nullable=False),
        sa.Column("fee_gold", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'passed', 'failed')", name="ck_vote_status"
        ),
        sa.CheckConstraint(
            "yes_weight >= 0 AND no_weight >= 0 AND fee_gold >= 0 AND "
            "eligible_weight > 0 AND yes_weight + no_weight <= eligible_weight",
            name="ck_vote_weights",
        ),
    )
    op.create_index(
        "uq_open_realm_vote",
        "realm_votes",
        ["realm_id"],
        unique=True,
        sqlite_where=sa.text("status = 'open'"),
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_table(
        "realm_vote_eligibility",
        sa.Column(
            "vote_id", sa.Uuid(), sa.ForeignKey("realm_votes.id"), primary_key=True
        ),
        sa.Column(
            "character_id", sa.Uuid(), sa.ForeignKey("characters.id"), primary_key=True
        ),
        sa.Column("weight", sa.BigInteger(), nullable=False),
        sa.Column("voted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("weight > 0", name="ck_vote_eligibility_weight"),
    )


def downgrade() -> None:
    """Remove ballots and snapshots."""
    op.drop_table("realm_vote_eligibility")
    op.drop_index("uq_open_realm_vote", table_name="realm_votes")
    op.drop_table("realm_votes")
