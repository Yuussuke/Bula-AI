"""Shared-source review and administrative designation, without changing existing data."""

from alembic import op
import sqlalchemy as sa

revision: str = "e610a130b001"
down_revision: str = "d510a102b002"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # Native PostgreSQL enum DDL is not expressible through portable alter_column.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'contributor'")
    op.create_table(
        "shared_bula_submissions",
        sa.Column(
            "bula_id",
            sa.Uuid(),
            sa.ForeignKey("bulas.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("source_description", sa.String(1000), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("content_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "review_status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("presentation", sa.Text(), nullable=True),
        sa.Column("strength", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "review_status IN ('pending','approved','rejected','withdrawn')",
            name=op.f("ck_shared_bula_submissions_valid_shared_review_status"),
        ),
    )
    op.create_index(
        "ix_shared_bula_submissions_review_status",
        "shared_bula_submissions",
        ["review_status"],
    )
    op.create_table(
        "bula_curation_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "bula_id",
            sa.Uuid(),
            sa.ForeignKey("bulas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_name", sa.String(255), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_bula_curation_events_bula_id", "bula_curation_events", ["bula_id"]
    )
    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("previous_role", sa.String(20), nullable=False),
        sa.Column("assigned_role", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        users = sa.table("users", sa.column("role"))
        contributors = connection.scalar(
            sa.select(sa.func.count())
            .select_from(users)
            .where(sa.cast(users.c.role, sa.Text()) == "contributor")
        )
        if contributors:
            raise RuntimeError(
                "Reassign contributor accounts explicitly before downgrading."
            )
    op.drop_table("user_role_assignments")
    op.drop_index("ix_bula_curation_events_bula_id", table_name="bula_curation_events")
    op.drop_table("bula_curation_events")
    op.drop_index(
        "ix_shared_bula_submissions_review_status", table_name="shared_bula_submissions"
    )
    op.drop_table("shared_bula_submissions")
    if connection.dialect.name == "postgresql":
        # PostgreSQL cannot remove one enum value; rebuild only after the guard.
        op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
        op.execute("ALTER TYPE userrole RENAME TO userrole_with_contributor")
        op.execute("CREATE TYPE userrole AS ENUM ('user', 'admin', 'reviewer')")
        op.execute(
            "ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole"
        )
        op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'::userrole")
        op.execute("DROP TYPE userrole_with_contributor")
