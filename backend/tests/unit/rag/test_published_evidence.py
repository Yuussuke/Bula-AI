"""Filters apply before the vector Top-K and metadata never becomes evidence."""

from uuid import UUID

import pytest
from langchain_core.documents import Document
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.evidence_units import build_evidence_units, format_evidence_units
from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id
from app.modules.rag.retriever import DenseBulaRetriever
from tests.integration.rag.test_corpus_retrieval import FixedEmbeddings


@pytest.mark.anyio
async def test_allowed_ids_precede_dense_candidate_budget() -> None:
    client = AsyncQdrantClient(location=":memory:")
    adapter = EmbeddingAdapter(embedder=FixedEmbeddings(), dimension=4)
    store = QdrantVectorStore(client=client, vector_size=4)
    await store.ensure_collection()
    allowed = UUID(int=100)
    try:
        await store.upsert_points(
            [
                PointStruct(
                    id=make_point_id(str(number)),
                    vector=[1.0, 0.0, 0.0, 0.0]
                    if number < 100
                    else [0.8, 0.2, 0.0, 0.0],
                    payload={
                        "chunk_id": str(number),
                        "bula_id": str(UUID(int=number)),
                        "corpus": "system",
                        "embedding_profile": adapter.embedding_profile,
                        "section_title": "Indicações",
                        "chunk_text": "Informação original.",
                    },
                )
                for number in range(1, 101)
            ]
        )
        retriever = DenseBulaRetriever(
            bula_id=None,
            corpus=(BulaCorpus.SYSTEM,),
            allowed_bula_ids=(allowed,),
            embeddings=adapter,
            qdrant_store=store,
            candidate_limit=1,
            k=1,
        )
        documents = await retriever.ainvoke("pergunta")
        assert [document.metadata["bula_id"] for document in documents] == [
            str(allowed)
        ]
        retriever.allowed_bula_ids = ()
        assert await retriever.ainvoke("pergunta") == []
    finally:
        await client.close()


def test_cross_bula_identity_is_local_to_each_source_without_changing_unit_text() -> (
    None
):
    documents = [
        Document(
            page_content="Orientação original.",
            metadata={
                "cross_bula": True,
                "drug_name": name,
                "manufacturer": manufacturer,
                "presentation": presentation,
                "section_title": "Advertências",
            },
        )
        for name, manufacturer, presentation in [
            ("Produto A", "Fabricante A", "gotas"),
            ("Produto B", "Fabricante B", "comprimidos"),
        ]
    ]
    units = build_evidence_units(documents)
    assert [unit.text for unit in units] == [
        "Orientação original.",
        "Orientação original.",
    ]
    formatted = format_evidence_units(units)
    assert (
        "[E1] Fonte 1; drug_name: Produto A; manufacturer: Fabricante A; presentation: gotas; seção:"
        in formatted
    )
    assert (
        "[E2] Fonte 2; drug_name: Produto B; manufacturer: Fabricante B; presentation: comprimidos; seção:"
        in formatted
    )
    scoped = format_evidence_units(
        build_evidence_units(
            [
                Document(
                    page_content="Texto original.", metadata={"section_title": "Seção"}
                )
            ]
        )
    )
    assert scoped == "[E1] Fonte 1; seção: Seção; tipo: prose\nTexto original."
