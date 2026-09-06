"""add sources to chat messages

Revision ID: a4f8c2d9e1b7
Revises: f7c2a9e4d1b6
Create Date: 2026-09-05 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a4f8c2d9e1b7"
down_revision: Union[str, Sequence[str], None] = "f7c2a9e4d1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "source_chunks",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "source_chunks")
