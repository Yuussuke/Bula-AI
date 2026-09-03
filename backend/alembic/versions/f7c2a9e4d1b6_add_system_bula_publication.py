"""add system bula publication

Revision ID: f7c2a9e4d1b6
Revises: d6a3f0b8c9e1
Create Date: 2026-09-01 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f7c2a9e4d1b6"
down_revision: Union[str, Sequence[str], None] = "d6a3f0b8c9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    publication_state = sa.Enum(
        "staged",
        "vetted",
        "published",
        "withdrawn",
        "rejected",
        name="systembulapublicationstate",
    )

    op.create_table(
        "system_bula_publications",
        sa.Column("bula_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            publication_state,
            server_default="staged",
            nullable=False,
        ),
        sa.Column("target_id", sa.String(length=255), nullable=False),
        sa.Column("active_ingredient", sa.String(length=500), nullable=False),
        sa.Column("product_name", sa.String(length=500), nullable=False),
        sa.Column("strength", sa.String(length=255), nullable=False),
        sa.Column("pharmaceutical_form", sa.String(length=500), nullable=False),
        sa.Column("presentation", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(length=20), nullable=False),
        sa.Column("manufacturer", sa.String(length=500), nullable=False),
        sa.Column("company_tax_id", sa.String(length=32), nullable=False),
        sa.Column("anvisa_product_id", sa.Integer(), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=False),
        sa.Column("process_number", sa.String(length=100), nullable=False),
        sa.Column("expedition_number", sa.String(length=100), nullable=False),
        sa.Column("transaction_number", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.String(length=100), nullable=False),
        sa.Column("canonical_source_url", sa.String(length=2048), nullable=False),
        sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("search_query", sa.String(length=500), nullable=False),
        sa.Column("downloader_version", sa.String(length=100), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column("content_size_bytes", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_name", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("published_by_user_id", sa.Integer(), nullable=True),
        sa.Column("published_by_name", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawal_reason", sa.Text(), nullable=True),
        sa.Column("supersedes_bula_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bula_id"],
            ["bulas.id"],
            name=op.f("fk_system_bula_publications_bula_id_bulas"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"],
            ["users.id"],
            name=op.f("fk_system_bula_publications_published_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name=op.f("fk_system_bula_publications_reviewed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_bula_id"],
            ["bulas.id"],
            name=op.f("fk_system_bula_publications_supersedes_bula_id_bulas"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("bula_id", name=op.f("pk_system_bula_publications")),
    )
    op.create_index(
        op.f("ix_system_bula_publications_sha256_checksum"),
        "system_bula_publications",
        ["sha256_checksum"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_bula_publications_source_record_id"),
        "system_bula_publications",
        ["source_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_bula_publications_state"),
        "system_bula_publications",
        ["state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_bula_publications_target_id"),
        "system_bula_publications",
        ["target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_system_bula_publications_target_id"),
        table_name="system_bula_publications",
    )
    op.drop_index(
        op.f("ix_system_bula_publications_state"),
        table_name="system_bula_publications",
    )
    op.drop_index(
        op.f("ix_system_bula_publications_source_record_id"),
        table_name="system_bula_publications",
    )
    op.drop_index(
        op.f("ix_system_bula_publications_sha256_checksum"),
        table_name="system_bula_publications",
    )
    op.drop_table("system_bula_publications")

    publication_state = sa.Enum(
        "staged",
        "vetted",
        "published",
        "withdrawn",
        "rejected",
        name="systembulapublicationstate",
    )
    publication_state.drop(op.get_bind(), checkfirst=True)
