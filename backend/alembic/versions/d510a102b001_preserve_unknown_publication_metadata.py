"""Preserve unknown acquisition metadata for verified corpus imports."""

from alembic import op

revision: str = "d510a102b001"
down_revision: str = "c46a1021b001"
branch_labels: None = None
depends_on: None = None

OPTIONAL_COLUMNS = (
    "manufacturer",
    "expedition_number",
    "transaction_number",
    "source_record_id",
    "source_published_at",
    "search_query",
    "downloader_version",
    "downloaded_at",
)


def upgrade() -> None:
    for column in OPTIONAL_COLUMNS:
        op.alter_column("system_bula_publications", column, nullable=True)


def downgrade() -> None:
    # Existing null values must be resolved explicitly before downgrading.
    # Never invent provenance values to satisfy the earlier constraint.
    for column in OPTIONAL_COLUMNS:
        op.alter_column("system_bula_publications", column, nullable=False)
