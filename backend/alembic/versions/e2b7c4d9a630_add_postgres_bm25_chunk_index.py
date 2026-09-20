"""Add real BM25 chunk index using pg_textsearch, not ts_rank_cd.

Revision ID: e2b7c4d9a630
Revises: b9d4e6f8a1c2
"""

from alembic import op
import sqlalchemy as sa

revision: str = "e2b7c4d9a630"
down_revision: str | None = "b9d4e6f8a1c2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Extension/configuration DDL has no SQLAlchemy Core equivalent. All SQL
    # here is static; user input never enters these statements.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_textsearch")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        "CREATE TEXT SEARCH CONFIGURATION public.bula_portuguese "
        "(COPY = pg_catalog.portuguese)"
    )
    op.execute(
        "ALTER TEXT SEARCH CONFIGURATION public.bula_portuguese "
        "ALTER MAPPING FOR hword, hword_part, word "
        "WITH public.unaccent, pg_catalog.portuguese_stem"
    )
    op.create_table(
        "chunk_meta",
        sa.Column("chunk_id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), nullable=False),
        sa.Column(
            "bula_id",
            sa.Uuid(),
            sa.ForeignKey("bulas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("corpus", sa.String(20), nullable=False),
        sa.Column("drug_name", sa.Text(), nullable=True),
        sa.Column("section_title", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "corpus IN ('private', 'system', 'shared')",
            name=op.f("ck_chunk_meta_valid_corpus"),
        ),
    )
    op.create_index("ix_chunk_meta_bula_id", "chunk_meta", ["bula_id"])
    op.create_index("ix_chunk_meta_corpus", "chunk_meta", ["corpus"])
    op.create_index(
        "ix_chunk_meta_bm25",
        "chunk_meta",
        ["chunk_text"],
        postgresql_using="bm25",
        postgresql_with={"text_config": "'public.bula_portuguese'"},
    )


def downgrade() -> None:
    op.drop_table("chunk_meta")
    op.execute("DROP TEXT SEARCH CONFIGURATION public.bula_portuguese")
    # Extensions belong to the infrastructure and may have other consumers.
