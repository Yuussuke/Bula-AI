"""Real PostgreSQL tests. Requires migrations and BM25_TEST_DATABASE_URL.

Only uniquely named test users/bulas are created and removed. No production
database defaults, schema drops, or table-wide truncates are used.
"""

import asyncio
import os
import sys
from collections import Counter
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from qdrant_client import AsyncQdrantClient

from app.modules.auth.models import User
from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.modules.rag.bm25_index import PostgreSQLBM25Index
from app.modules.rag.bm25_retriever import BM25Retriever
from app.modules.rag.dependencies import get_bm25_index, get_bm25_retriever_factory
from app.modules.rag.models import ChunkMetadata
from app.modules.rag.repository import (
    ChunkIndexPersistenceError,
    ChunkMetadataRepository,
)
from app.modules.rag.schemas import ChunkMetadataInput
from app.modules.rag.backfill_service import ChunkMetadataBackfillService
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.qdrant_store import QdrantVectorStore, build_qdrant_point
from app.modules.rag.schemas import DocumentChunk

BM25Context = tuple[PostgreSQLBM25Index, AsyncSession, list[Bula]]


@pytest.fixture
async def bm25_context() -> AsyncIterator[
    tuple[PostgreSQLBM25Index, AsyncSession, list[Bula]]
]:
    database_url = os.getenv("BM25_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "Set BM25_TEST_DATABASE_URL to a migrated isolated PostgreSQL database."
        )
    if "test" not in (make_url(database_url).database or ""):
        pytest.fail("BM25 test database name must contain 'test'.")
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as db:
        user = User(
            email=f"bm25-{uuid4().hex}@example.com",
            full_name="BM25 Test",
            hashed_password="not-a-login-credential",
        )
        db.add(user)
        await db.flush()
        bulas = [
            Bula(
                id=uuid4(),
                user_id=user.id,
                drug_name="Dipirona",
                status=BulaStatus.READY,
                corpus=corpus,
            )
            for corpus in (BulaCorpus.PRIVATE, BulaCorpus.SYSTEM, BulaCorpus.SHARED)
        ]
        db.add_all(bulas)
        await db.commit()
        test_user_id = user.id
        try:
            yield PostgreSQLBM25Index(ChunkMetadataRepository(db)), db, bulas
        finally:
            await db.rollback()
            await db.execute(delete(User).where(User.id == test_user_id))
            await db.commit()
    await engine.dispose()


def make_chunk(bula: Bula, source_text: str, suffix: str = "a") -> ChunkMetadataInput:
    return ChunkMetadataInput(
        chunk_id=f"{bula.id}:{suffix}",
        doc_id=str(bula.id),
        bula_id=bula.id,
        corpus=bula.corpus,
        drug_name=bula.drug_name,
        section_title="Advertências",
        chunk_text=source_text,
    )


@pytest.mark.anyio
async def test_real_bm25_portuguese_accents_stemming_and_nonmatches(
    bm25_context: BM25Context,
) -> None:
    index, db, bulas = bm25_context
    await index.upsert_chunks(
        [
            make_chunk(
                bulas[0], "Contraindicações da DIPIRONA SÓDICA para pacientes.", "a"
            ),
            make_chunk(bulas[0], "Armazenar longe do calor e da umidade.", "b"),
        ]
    )
    for query in ("dipirona sodica", "DIPIRONA SÓDICA", "paciente"):
        results = await index.search(query, bula_id=bulas[0].id)
        assert [result.chunk_id for result in results] == [f"{bulas[0].id}:a"], query
        assert results[0].bm25_score > 0
        assert results[0].section_title == "Advertências"
    assert await index.search("ornitorrinco", bula_id=bulas[0].id) == []
    assert await index.search("e de a", bula_id=bulas[0].id) == []
    assert await index.search("  ", bula_id=bulas[0].id) == []
    # Static catalog query proves the actual access method, not ts_rank_cd.
    access_method = await db.scalar(
        text(
            "SELECT am.amname FROM pg_class c JOIN pg_am am ON am.oid = c.relam "
            "WHERE c.oid = 'public.ix_chunk_meta_bm25'::regclass"
        )
    )
    assert access_method == "bm25"


@pytest.mark.anyio
async def test_filtered_top_k_and_corpus_isolation(bm25_context: BM25Context) -> None:
    index, _, bulas = bm25_context
    unique_term = f"seletor{uuid4().hex}"
    await index.upsert_chunks(
        [
            make_chunk(
                bula,
                f"{unique_term} " * (number + 1) + "cuidados especiais",
                str(number),
            )
            for bula in bulas
            for number in range(12)
        ]
    )
    results = await index.search(unique_term, bula_id=bulas[0].id, k=5)
    assert len(results) == 5
    assert {result.bula_id for result in results} == {bulas[0].id}
    assert [result.bm25_score for result in results] == sorted(
        [result.bm25_score for result in results], reverse=True
    )
    assert results == await index.search(unique_term, bula_id=bulas[0].id, k=5)
    results = await index.search(
        unique_term, corpus=[BulaCorpus.SYSTEM, BulaCorpus.SHARED], k=100
    )
    assert len(results) == 24
    assert {result.corpus for result in results} == {
        BulaCorpus.SYSTEM,
        BulaCorpus.SHARED,
    }
    assert await index.search(unique_term, corpus=[]) == []
    assert (
        await index.search(unique_term, bula_id=bulas[0].id, corpus=[BulaCorpus.SYSTEM])
        == []
    )


@pytest.mark.anyio
async def test_upsert_updates_without_duplicates_and_survives_new_session(
    bm25_context: BM25Context,
) -> None:
    index, db, bulas = bm25_context
    chunk = make_chunk(bulas[0], "dipirona")
    await index.upsert_chunks([chunk])
    await index.upsert_chunks([chunk.model_copy(update={"chunk_text": "amoxicilina"})])
    count = await db.scalar(
        select(func.count())
        .select_from(ChunkMetadata)
        .where(ChunkMetadata.bula_id == bulas[0].id)
    )
    assert count == 1
    async with AsyncSession(db.bind, expire_on_commit=False) as fresh_session:
        fresh_index = PostgreSQLBM25Index(ChunkMetadataRepository(fresh_session))
        assert await fresh_index.search("dipirona", bula_id=bulas[0].id) == []
        results = await fresh_index.search("amoxicilina", bula_id=bulas[0].id)
        assert results[0].chunk_text == "amoxicilina"


@pytest.mark.anyio
async def test_replace_prunes_old_chunks_and_corpus_update_changes_filters(
    bm25_context: BM25Context,
) -> None:
    index, _, bulas = bm25_context
    await index.upsert_chunks([make_chunk(bulas[0], "dipirona", "old")])
    await index.replace_bula_chunks(
        bula_id=bulas[0].id, chunks=[make_chunk(bulas[0], "amoxicilina", "new")]
    )
    assert await index.search("dipirona", bula_id=bulas[0].id) == []
    await index.update_corpus(bula_id=bulas[0].id, corpus=BulaCorpus.SHARED)
    assert (
        await index.search(
            "amoxicilina", bula_id=bulas[0].id, corpus=[BulaCorpus.PRIVATE]
        )
        == []
    )
    assert (
        len(
            await index.search(
                "amoxicilina", bula_id=bulas[0].id, corpus=[BulaCorpus.SHARED]
            )
        )
        == 1
    )


@pytest.mark.anyio
async def test_cross_bula_collision_rolls_back_entire_batch(
    bm25_context: BM25Context,
) -> None:
    index, _, bulas = bm25_context
    original_bula_id, other_bula_id = bulas[0].id, bulas[1].id
    original = make_chunk(bulas[0], "dipirona")
    await index.upsert_chunks([original])
    collision = make_chunk(bulas[1], "amoxicilina").model_copy(
        update={"chunk_id": original.chunk_id}
    )
    with pytest.raises(ValueError, match="another bula"):
        await index.upsert_chunks(
            [
                make_chunk(bulas[1], "omeprazol", f"new-{number}")
                for number in range(100)
            ]
            + [collision]
        )
    assert await index.search("omeprazol", bula_id=other_bula_id) == []
    assert len(await index.search("dipirona", bula_id=original_bula_id)) == 1


@pytest.mark.anyio
async def test_database_failure_does_not_expose_source_in_worker_error(
    bm25_context: BM25Context,
) -> None:
    index, _, bulas = bm25_context
    unknown_bula_id = uuid4()
    chunk = make_chunk(bulas[0], "private source text").model_copy(
        update={"bula_id": unknown_bula_id, "doc_id": str(unknown_bula_id)}
    )
    with pytest.raises(ChunkIndexPersistenceError) as captured:
        await index.upsert_chunks([chunk])
    assert "private source text" not in str(captured.value)
    assert captured.value.__cause__ is None


@pytest.mark.anyio
async def test_backfill_database_listing_paginates_only_ready_bulas(
    bm25_context: BM25Context,
) -> None:
    _, db, bulas = bm25_context
    bulas[0].status = BulaStatus.PROCESSING
    await db.commit()
    repository = BulaRepository(db)
    seen_ids = []
    after_id = None
    while True:
        page = await repository.list_ready_bulas_for_indexing(
            after_id=after_id, limit=2
        )
        if not page:
            break
        assert len(page) <= 2
        assert all(bula.status == BulaStatus.READY for bula in page)
        seen_ids.extend(bula.id for bula in page)
        after_id = page[-1].id
    assert seen_ids == sorted(set(seen_ids))
    assert bulas[0].id not in seen_ids
    assert bulas[1].id in seen_ids
    assert bulas[2].id in seen_ids


@pytest.mark.anyio
async def test_bula_deletion_cascades_and_query_is_parameterized(
    bm25_context: BM25Context,
) -> None:
    index, db, bulas = bm25_context
    await index.upsert_chunks([make_chunk(bulas[0], "dipirona")])
    await index.search("'); DROP TABLE chunk_meta; --", bula_id=bulas[0].id)
    assert len(await index.search("dipirona", bula_id=bulas[0].id)) == 1
    await db.execute(delete(Bula).where(Bula.id == bulas[0].id))
    await db.commit()
    assert await index.search("dipirona", bula_id=bulas[0].id) == []


@pytest.mark.anyio
async def test_qdrant_backfill_is_idempotent_and_does_not_change_source(
    bm25_context: BM25Context,
) -> None:
    index, db, bulas = bm25_context
    # Real Qdrant client in local mode; PostgreSQL/pg_textsearch remain real.
    client = AsyncQdrantClient(location=":memory:")
    store = QdrantVectorStore(client=client, vector_size=4)
    try:
        await store.ensure_collection()
        source = "## Composição\nDipirona sódica: 500 mg.\n"
        chunk = DocumentChunk(
            chunk_id=f"{bulas[0].id}:original",
            doc_id=str(bulas[0].id),
            index=0,
            text=source,
            chunk_title="Composição",
            section_title="Composição",
            token_estimate=10,
            method="deterministic",
            metadata={},
        )
        point = build_qdrant_point(
            bula=bulas[0],
            chunk=chunk,
            vector=[0.1, 0.2, 0.3, 0.4],
            embedding_profile="test",
        )
        await store.upsert_points([point])
        service = ChunkMetadataBackfillService(
            bula_repository=BulaRepository(db), qdrant_store=store, bm25_index=index
        )
        preview = await service.backfill(
            bula_id=bulas[0].id, batch_size=1, is_dry_run=True
        )
        assert preview.chunk_count == 1
        assert await index.search("dipirona", bula_id=bulas[0].id) == []
        for _ in range(2):
            result = await service.backfill(bula_id=bulas[0].id, batch_size=1)
            assert result.chunk_count == 1
        matches = await index.search("sodica", bula_id=bulas[0].id)
        assert len(matches) == 1
        assert matches[0].chunk_id == chunk.chunk_id
        assert matches[0].chunk_text == source
        assert (await store.list_points_for_bula(bula_id=str(bulas[0].id)))[
            0
        ].payload == point.payload
        assert bulas[0].status == BulaStatus.READY
    finally:
        await client.close()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "query", ["paracetamol", "paracetamol 500", "SODICA", "sódica", "paciente"]
)
async def test_bm25_retriever_keyword_accents_and_stemming(
    bm25_context: BM25Context, query: str
) -> None:
    index, db, bulas = bm25_context
    source = "## Composição\nParacetamol 500mg; substância sódica para pacientes.\n"
    chunk = make_chunk(bulas[0], source)
    await index.upsert_chunks([chunk])
    # Exercise the same scoped dependency factories used by future consumers.
    factory = get_bm25_retriever_factory(index=get_bm25_index(db=db))
    documents = await factory.build(bula_id=bulas[0].id).ainvoke(query)
    assert len(documents) == 1
    assert documents[0].page_content == source
    assert documents[0].id == chunk.chunk_id
    assert documents[0].metadata["bula_id"] == str(bulas[0].id)
    assert documents[0].metadata["section_title"] == chunk.section_title
    assert documents[0].metadata["bm25_score"] > 0
    assert documents[0].metadata["score"] == documents[0].metadata["bm25_score"]


@pytest.mark.anyio
async def test_normalization_keeps_token_frequency_and_numeric_distinctions(
    bm25_context: BM25Context,
) -> None:
    _, db, _ = bm25_context

    async def normalize(source: str) -> str:
        value = await db.scalar(select(func.public.bula_bm25_normalize_v2(source)))
        assert isinstance(value, str)
        return value

    single = Counter((await normalize("dipirona")).split())
    repeated = Counter((await normalize("dipirona " * 300)).split())
    assert single
    assert repeated == Counter({term: count * 300 for term, count in single.items()})
    for first, second in [("500", "50"), ("0.5", "5"), ("10-20", "1020"), ("mg", "mL")]:
        assert await normalize(first) != await normalize(second)
    assert await normalize("e de a") == ""
    assert await normalize("") == ""


@pytest.mark.anyio
async def test_search_text_is_internal_and_tracks_source_updates(
    bm25_context: BM25Context,
) -> None:
    index, db, bulas = bm25_context
    source = "## Posologia\n| Dose | Volume |\n| 500 mg | 0,5 mL |\nContraindicações.\n"
    chunk = make_chunk(bulas[0], source)
    await index.upsert_chunks([chunk])
    documents = await BM25Retriever(index=index, bula_id=bulas[0].id).ainvoke(
        "contraindicação"
    )
    assert documents[0].page_content == source
    assert "search_text" not in documents[0].metadata

    # The database, not caller-supplied search terms, owns the derived column.
    await db.execute(
        update(ChunkMetadata)
        .where(ChunkMetadata.chunk_id == chunk.chunk_id)
        .values(chunk_text="Amoxicilina 50 mg.", search_text="forged normalization")
    )
    await db.commit()
    assert await index.search("contraindicação", bula_id=bulas[0].id) == []
    assert await index.search("500", bula_id=bulas[0].id) == []
    assert await index.search("dipirona", bula_id=bulas[0].id) == []
    assert (await index.search("amoxicilina", bula_id=bulas[0].id))[
        0
    ].chunk_text == "Amoxicilina 50 mg."
    assert len(await index.search("50", bula_id=bulas[0].id)) == 1


@pytest.mark.anyio
async def test_normalization_migration_rebuilds_existing_chunks_without_source_changes(
    bm25_context: BM25Context,
) -> None:
    index, db, bulas = bm25_context
    database_url = os.environ["BM25_TEST_DATABASE_URL"]
    # The fixture already requires an explicit isolated database named *test*.
    # Run serially: this test migrates that test database, never the application.
    source = "## Contraindicações\nTexto original: 500 mg, 0,5 mL; 10–20 kg.\n"
    chunk = make_chunk(bulas[0], source)
    await index.upsert_chunks([chunk])
    other_chunk = make_chunk(bulas[0], "Advertências: texto preexistente.", "legacy")

    async def migrate(direction: str, revision: str) -> None:
        await db.close()  # Release locks and prepared statements before DDL.
        migration_environment = {
            **os.environ,
            "DATABASE_URL": database_url,
            "SECRET_KEY": "bm25-migration-test-only-not-a-real-secret",
        }
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "alembic",
            direction,
            revision,
            cwd=Path(__file__).resolve().parents[3],
            env=migration_environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=60)
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise
        assert process.returncode == 0, output.decode(errors="replace")

    try:
        await migrate("downgrade", "e2b7c4d9a630")
        # Insert through the pre-v2 schema to prove existing rows are backfilled.
        await db.execute(insert(ChunkMetadata).values(**other_chunk.model_dump()))
        await db.commit()
        preserved = await db.scalar(
            select(ChunkMetadata.chunk_text).where(
                ChunkMetadata.chunk_id == chunk.chunk_id
            )
        )
        assert preserved == source
    finally:
        await migrate("upgrade", "head")

    matches = await index.search("contraindicação", bula_id=bulas[0].id)
    assert len(matches) == 1
    assert matches[0].chunk_id == chunk.chunk_id
    assert matches[0].chunk_text == source
    assert (await index.search("advertência", bula_id=bulas[0].id))[
        0
    ].chunk_text == other_chunk.chunk_text


@pytest.mark.anyio
async def test_bm25_retriever_scopes_top_k_and_order(bm25_context: BM25Context) -> None:
    index, _, bulas = bm25_context
    term = f"retrieval{uuid4().hex}"
    await index.upsert_chunks(
        [
            make_chunk(bula, f"{term} " * (number + 1) + "cuidados", str(number))
            for bula in bulas
            for number in range(4)
        ]
    )
    retriever = BM25Retriever(index=index, bula_id=bulas[0].id, k=2)
    documents = await retriever.ainvoke(term)
    assert len(documents) == 2
    assert {document.metadata["bula_id"] for document in documents} == {
        str(bulas[0].id)
    }
    scores = [document.metadata["score"] for document in documents]
    assert scores == sorted(scores, reverse=True)
    assert documents == await retriever.ainvoke(term)

    corpus_retriever = BM25Retriever(
        index=index, corpus=(BulaCorpus.SHARED, BulaCorpus.SYSTEM), k=10
    )
    documents = await corpus_retriever.ainvoke(term)
    assert len(documents) == 8
    assert {document.metadata["corpus"] for document in documents} == {
        "shared",
        "system",
    }
    assert str(bulas[0].id) not in {
        document.metadata["bula_id"] for document in documents
    }

    contradictory_scope = BM25Retriever(
        index=index, bula_id=bulas[0].id, corpus=(BulaCorpus.SYSTEM,)
    )
    assert await contradictory_scope.ainvoke(term) == []


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["paracetamois", "ornitorrinco", "e de a", "", "  "])
async def test_bm25_retriever_returns_no_matches(
    bm25_context: BM25Context, query: str
) -> None:
    index, _, bulas = bm25_context
    await index.upsert_chunks([make_chunk(bulas[0], "paracetamol 500mg")])
    retriever = BM25Retriever(index=index, bula_id=bulas[0].id)
    assert await retriever.ainvoke(query) == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("source", "query"),
    [
        ("Contraindicações", "contraindicação"),
        ("Contraindicação", "contraindicações"),
        ("Contraindicações", "contraindicacoes"),
        ("contraindicacoes", "contraindicações"),
        ("Contraindicação", "contraindicacao"),
        ("contraindicacao", "contraindicação"),
        ("Informações", "informação"),
        ("Advertências", "advertência"),
        ("sódica", "sodica"),
        ("sodica", "sódica"),
    ],
)
async def test_bm25_retriever_contraindicacao_inflections(
    bm25_context: BM25Context,
    source: str,
    query: str,
) -> None:
    index, _, bulas = bm25_context
    await index.upsert_chunks([make_chunk(bulas[0], source)])
    retriever = BM25Retriever(index=index, bula_id=bulas[0].id)
    documents = await retriever.ainvoke(query)
    assert len(documents) == 1
    assert documents[0].page_content == source
