"""Add guest identity and activity tracking."""

import sqlalchemy as sa
from alembic import op

revision = "0003_guests"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow credential-free accounts and constrain the identity kind."""
    with op.batch_alter_table("users") as batch:
        batch.alter_column("email", existing_type=sa.String(320), nullable=True)
        batch.alter_column("password_hash", existing_type=sa.String(512), nullable=True)
        batch.add_column(
            sa.Column("kind", sa.String(16), nullable=False, server_default="full")
        )
        batch.add_column(sa.Column("last_activity_at", sa.DateTime(timezone=True)))
        batch.create_check_constraint("ck_users_kind", "kind IN ('guest', 'full')")


def downgrade() -> None:
    """Remove disposable guest users before restoring required credentials."""
    op.execute(
        "DELETE FROM refresh_tokens WHERE user_id IN "
        "(SELECT id FROM users WHERE kind = 'guest')"
    )
    op.execute("DELETE FROM users WHERE kind = 'guest'")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_kind", type_="check")
        batch.drop_column("last_activity_at")
        batch.drop_column("kind")
        batch.alter_column("email", existing_type=sa.String(320), nullable=False)
        batch.alter_column(
            "password_hash", existing_type=sa.String(512), nullable=False
        )
