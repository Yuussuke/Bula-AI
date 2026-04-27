"""add role to users

Revision ID: b4e6c8d9a0f1
Revises: a7c9d2e4f6b8
Create Date: 2026-04-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4e6c8d9a0f1"
down_revision: Union[str, Sequence[str], None] = "a7c9d2e4f6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = sa.Enum("user", "admin", "reviewer", name="userrole")


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "role",
            user_role_enum,
            server_default="user",
            nullable=True,
        ),
    )
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    op.alter_column(
        "users",
        "role",
        existing_type=user_role_enum,
        server_default="user",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "role")

    bind = op.get_bind()
    user_role_enum.drop(bind, checkfirst=True)
