"""Add the standing combat stance."""

import sqlalchemy as sa
from alembic import op

from app.config import CONTENT_DIR
from app.content.loader import load_content

revision = "v08_0015_stance"
down_revision = "v08_0014_consumables_hp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Initialize existing characters from content before requiring the setting."""
    default_stance = load_content(CONTENT_DIR).progression.default_stance
    op.add_column(
        "characters",
        sa.Column("stance", sa.String(128), nullable=True),
    )
    characters = sa.table("characters", sa.column("stance", sa.String(128)))
    op.execute(characters.update().values(stance=default_stance))
    with op.batch_alter_table("characters") as batch:
        batch.alter_column("stance", existing_type=sa.String(128), nullable=False)


def downgrade() -> None:
    """Remove the character setting."""
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("stance")
