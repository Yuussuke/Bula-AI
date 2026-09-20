"""Preserve Portuguese inflections alongside accent-insensitive BM25 terms.

Revision ID: f6c8d2a91b40
Revises: e2b7c4d9a630
"""

from alembic import op
import sqlalchemy as sa

revision: str = "f6c8d2a91b40"
down_revision: str | None = "e2b7c4d9a630"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # SQL functions/triggers have no Core DDL equivalent. These static statements
    # contain no user input. STABLE is intentional: unaccent is NOT immutable.
    # Version the function instead of changing normalization under a live index.
    op.execute("""
        CREATE FUNCTION public.bula_bm25_normalize_v2(source_text text)
        RETURNS text LANGUAGE sql STABLE STRICT PARALLEL SAFE
        SET search_path = pg_catalog, public
        AS $function$
            SELECT coalesce(string_agg(
                stream.prefix || encode(convert_to(
                    public.unaccent('public.unaccent'::regdictionary, term.lexeme),
                    'UTF8'
                ), 'hex'),
                ' ' ORDER BY stream.prefix, token.ordinality, term.ordinality
            ), '')
            FROM pg_catalog.ts_debug('pg_catalog.portuguese'::regconfig, source_text)
                WITH ORDINALITY AS token
            CROSS JOIN LATERAL (
                SELECT 'p' AS prefix, token.lexemes
                UNION ALL
                SELECT 'f', CASE
                    WHEN 'pg_catalog.portuguese_stem'::regdictionary
                        = ANY(token.dictionaries)
                    THEN pg_catalog.ts_lexize(
                        'pg_catalog.portuguese_stem'::regdictionary,
                        public.unaccent('public.unaccent'::regdictionary, token.token)
                    )
                    ELSE token.lexemes
                END
            ) AS stream
            CROSS JOIN LATERAL unnest(stream.lexemes)
                WITH ORDINALITY AS term(lexeme, ordinality)
        $function$
    """)
    # Each original token occurrence contributes to its own stream. Do not use
    # tsvector_to_array (it deduplicates terms and corrupts BM25 term frequency).
    # Prefix + hex encodes a lexeme as one simple-parser token, even for values
    # such as 0.5 or -20. The two streams never collide with each other.
    op.add_column("chunk_meta", sa.Column("search_text", sa.Text(), nullable=True))
    op.execute("""
        UPDATE public.chunk_meta
        SET search_text = public.bula_bm25_normalize_v2(chunk_text)
    """)
    op.alter_column("chunk_meta", "search_text", nullable=False)
    op.execute("""
        CREATE FUNCTION public.bula_bm25_sync_search_text_v2()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            NEW.search_text := public.bula_bm25_normalize_v2(NEW.chunk_text);
            RETURN NEW;
        END
        $function$
    """)
    op.execute("""
        CREATE TRIGGER chunk_meta_sync_search_text_v2
        BEFORE INSERT OR UPDATE OF chunk_text, search_text ON public.chunk_meta
        FOR EACH ROW EXECUTE FUNCTION public.bula_bm25_sync_search_text_v2()
    """)
    op.drop_index("ix_chunk_meta_bm25", table_name="chunk_meta")
    op.create_index(
        "ix_chunk_meta_bm25",
        "chunk_meta",
        ["search_text"],
        postgresql_using="bm25",
        postgresql_with={"text_config": "'pg_catalog.simple'"},
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_meta_bm25", table_name="chunk_meta")
    op.execute("DROP TRIGGER chunk_meta_sync_search_text_v2 ON public.chunk_meta")
    op.execute("DROP FUNCTION public.bula_bm25_sync_search_text_v2()")
    op.drop_column("chunk_meta", "search_text")
    op.execute("DROP FUNCTION public.bula_bm25_normalize_v2(text)")
    op.create_index(
        "ix_chunk_meta_bm25",
        "chunk_meta",
        ["chunk_text"],
        postgresql_using="bm25",
        postgresql_with={"text_config": "'public.bula_portuguese'"},
    )
