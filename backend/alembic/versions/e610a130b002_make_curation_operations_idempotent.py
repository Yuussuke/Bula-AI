"""Atomic ingestion dispatch, idempotent decisions and documentary audit snapshots."""

from alembic import op
import sqlalchemy as sa

revision: str = "e610a130b002"
down_revision: str = "e610a130b001"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    submissions = sa.table(
        "shared_bula_submissions",
        sa.column("sha256_checksum"),
        sa.column("review_status"),
    )
    duplicates = (
        op.get_bind()
        .execute(
            sa.select(submissions.c.sha256_checksum)
            .where(submissions.c.review_status.in_(["pending", "approved"]))
            .group_by(submissions.c.sha256_checksum)
            .having(sa.func.count() > 1)
        )
        .first()
    )
    if duplicates is not None:
        raise RuntimeError(
            "Active duplicate shared PDFs require an explicit documentary decision before migration."
        )
    op.add_column(
        "shared_bula_submissions",
        sa.Column("ingestion_job_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "shared_bula_submissions",
        sa.Column("ingestion_operation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "shared_bula_submissions",
        sa.Column("supersedes_bula_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_shared_bula_submissions_supersedes_bula_id_bulas",
        "shared_bula_submissions",
        "bulas",
        ["supersedes_bula_id"],
        ["id"],
    )
    op.create_index(
        "uq_shared_active_pdf",
        "shared_bula_submissions",
        ["sha256_checksum"],
        unique=True,
        postgresql_where=sa.column("review_status").in_(["pending", "approved"]),
        sqlite_where=sa.column("review_status").in_(["pending", "approved"]),
    )
    # Historical events remain unchanged: absent author snapshots/keys stay NULL.
    op.alter_column(
        "bula_curation_events",
        "actor_name",
        existing_type=sa.String(255),
        type_=sa.Text(),
    )
    for table_name in ("bula_curation_events", "user_role_assignments"):
        op.add_column(table_name, sa.Column("actor_role", sa.String(20), nullable=True))
        op.add_column(table_name, sa.Column("operation_id", sa.Uuid(), nullable=True))
        op.add_column(
            table_name, sa.Column("request_fingerprint", sa.String(64), nullable=True)
        )
    op.add_column(
        "bula_curation_events", sa.Column("before_state", sa.JSON(), nullable=True)
    )
    op.add_column(
        "bula_curation_events", sa.Column("after_state", sa.JSON(), nullable=True)
    )
    op.add_column(
        "user_role_assignments", sa.Column("actor_name", sa.Text(), nullable=True)
    )
    op.create_unique_constraint(
        "uq_curation_actor_operation",
        "bula_curation_events",
        ["actor_id", "operation_id"],
    )
    op.create_unique_constraint(
        "uq_role_actor_operation", "user_role_assignments", ["actor_id", "operation_id"]
    )


def downgrade() -> None:
    for table_name in ("bula_curation_events", "user_role_assignments"):
        events = sa.table(table_name, sa.column("operation_id"))
        if op.get_bind().scalar(
            sa.select(sa.func.count())
            .select_from(events)
            .where(events.c.operation_id.is_not(None))
        ):
            raise RuntimeError(
                "Cannot discard recorded idempotency/audit data. Preserve it and authorize a rollback procedure explicitly."
            )
    op.drop_constraint(
        "uq_role_actor_operation", "user_role_assignments", type_="unique"
    )
    op.drop_constraint(
        "uq_curation_actor_operation", "bula_curation_events", type_="unique"
    )
    op.drop_column("user_role_assignments", "actor_name")
    op.drop_column("bula_curation_events", "after_state")
    op.drop_column("bula_curation_events", "before_state")
    for table_name in ("bula_curation_events", "user_role_assignments"):
        op.drop_column(table_name, "request_fingerprint")
        op.drop_column(table_name, "operation_id")
        op.drop_column(table_name, "actor_role")
    # Keep TEXT when rolling back: do not truncate legitimate historical names.
    op.drop_index("uq_shared_active_pdf", table_name="shared_bula_submissions")
    op.drop_constraint(
        "fk_shared_bula_submissions_supersedes_bula_id_bulas",
        "shared_bula_submissions",
        type_="foreignkey",
    )
    op.drop_column("shared_bula_submissions", "supersedes_bula_id")
    op.drop_column("shared_bula_submissions", "ingestion_operation_id")
    op.drop_column("shared_bula_submissions", "ingestion_job_id")
