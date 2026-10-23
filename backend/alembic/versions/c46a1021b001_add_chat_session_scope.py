"""Distinguish general conversations from sessions whose leaflet was deleted."""

from alembic import op
import sqlalchemy as sa

revision: str = "c46a1021b001"
down_revision: str = "f6c8d2a91b40"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("scope", sa.String(20), nullable=False, server_default="bula"),
    )
    op.create_check_constraint(
        "valid_chat_scope", "chat_sessions", "scope IN ('bula', 'cross_bula')"
    )
    op.create_check_constraint(
        "cross_bula_without_document",
        "chat_sessions",
        "scope != 'cross_bula' OR bula_id IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("cross_bula_without_document", "chat_sessions", type_="check")
    op.drop_constraint("valid_chat_scope", "chat_sessions", type_="check")
    op.drop_column("chat_sessions", "scope")
