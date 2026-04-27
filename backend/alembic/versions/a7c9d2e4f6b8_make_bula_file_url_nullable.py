"""make_bula_file_url_nullable

Revision ID: a7c9d2e4f6b8
Revises: f3a1b2c4d5e6
Create Date: 2026-04-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c9d2e4f6b8"
down_revision: Union[str, Sequence[str], None] = "f3a1b2c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "bulas",
        "file_url",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "bulas",
        "file_url",
        existing_type=sa.String(),
        nullable=False,
    )
