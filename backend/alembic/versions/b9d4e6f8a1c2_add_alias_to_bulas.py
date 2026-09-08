"""add alias to bulas

Revision ID: b9d4e6f8a1c2
Revises: a4f8c2d9e1b7
Create Date: 2026-09-07 16:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b9d4e6f8a1c2"
down_revision: Union[str, Sequence[str], None] = "a4f8c2d9e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bulas",
        sa.Column("alias", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bulas", "alias")
