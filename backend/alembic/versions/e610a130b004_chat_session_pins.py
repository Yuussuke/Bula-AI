"""Persist each owner's conversation pin preference."""

from alembic import op
import sqlalchemy as sa

revision: str = "e610a130b004"
down_revision: str = "e610a130b003"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "is_pinned")
