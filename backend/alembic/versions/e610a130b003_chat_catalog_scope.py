"""Persist the public catalog boundary of cross-bula conversations."""

from alembic import op
import sqlalchemy as sa

revision: str = "e610a130b003"
down_revision: str = "e610a130b002"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # Existing cross-bula conversations already searched both public corpora.
    op.add_column(
        "chat_sessions",
        sa.Column("catalog_scope", sa.String(10), nullable=False, server_default="all"),
    )
    op.create_check_constraint(
        "valid_catalog_scope",
        "chat_sessions",
        "catalog_scope IN ('all', 'system', 'shared')",
    )
    op.create_check_constraint(
        "individual_catalog_scope",
        "chat_sessions",
        "scope = 'cross_bula' OR catalog_scope = 'all'",
    )


def downgrade() -> None:
    sessions = sa.table("chat_sessions", sa.column("catalog_scope", sa.String(10)))
    restricted_session = (
        op.get_bind()
        .execute(
            sa.select(sessions.c.catalog_scope)
            .where(sessions.c.catalog_scope != "all")
            .limit(1)
        )
        .first()
    )
    if restricted_session is not None:
        raise RuntimeError(
            "Cannot discard catalog boundaries of existing conversations."
        )
    op.drop_constraint("individual_catalog_scope", "chat_sessions", type_="check")
    op.drop_constraint("valid_catalog_scope", "chat_sessions", type_="check")
    op.drop_column("chat_sessions", "catalog_scope")
