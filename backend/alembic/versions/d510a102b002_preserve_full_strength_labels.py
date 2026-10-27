"""Preserve complete multi-presentation concentration labels without truncation."""

from alembic import op
import sqlalchemy as sa

revision: str = "d510a102b002"
down_revision: str = "d510a102b001"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.alter_column(
        "system_bula_publications",
        "strength",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # PostgreSQL must reject longer values rather than truncate source metadata.
    op.alter_column(
        "system_bula_publications",
        "strength",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=False,
    )
