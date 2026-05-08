"""add chat session title and role check

Revision ID: d6a3f0b8c9e1
Revises: c8e91a4b2f6d
Create Date: 2026-05-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6a3f0b8c9e1"
down_revision: Union[str, Sequence[str], None] = "c8e91a4b2f6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "chat_sessions",
        sa.Column(
            "title",
            sa.String(length=50),
            server_default="Nova conversa",
            nullable=False,
        ),
    )
    op.alter_column(
        "chat_sessions",
        "title",
        existing_type=sa.String(length=50),
        existing_nullable=False,
        server_default=None,
    )

    # The historical migration created PostgreSQL's native chatrole enum with
    # USER/ASSISTANT/SYSTEM labels. Removing enum values is intentionally
    # avoided; this constraint blocks new SYSTEM rows at the table boundary.
    op.create_check_constraint(
        op.f("ck_chat_messages_role_user_assistant"),
        "chat_messages",
        "role IN ('USER', 'ASSISTANT')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("ck_chat_messages_role_user_assistant"),
        "chat_messages",
        type_="check",
    )
    op.drop_column("chat_sessions", "title")
