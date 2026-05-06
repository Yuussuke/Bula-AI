"""add bula error message and error status

Revision ID: c8e91a4b2f6d
Revises: fb64fbed5ae5
Create Date: 2026-05-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e91a4b2f6d"
down_revision: Union[str, Sequence[str], None] = "fb64fbed5ae5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "bulas",
        sa.Column("error_message", sa.String(length=1000), nullable=True),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE bulastatus ADD VALUE IF NOT EXISTS 'ERROR'")

        op.execute("UPDATE bulas SET status = 'ERROR' WHERE status = 'FAILED'")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("UPDATE bulas SET status = 'FAILED' WHERE status = 'ERROR'")

    op.drop_column("bulas", "error_message")
