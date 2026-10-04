"""Exercise scoped factories with Qdrant's in-memory filter engine.

The lexical index is an external-dependency stub; its real PostgreSQL corpus
filtering is covered separately in test_bm25_index.py. No provider is called.
"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from langchain_core.embeddings import Embeddings as LCEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.core.config import Settings
from app.modules.bulas.models import BulaCorpus
from app.modules.rag import dependencies
from app.modules.rag.bm25_retriever import BM25RetrieverFactory, BM25SearchIndex
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.qdrant_client import QDRANT_CLIENT_STATE_KEY
from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id
from app.modules.rag.retrieval_mode import RetrievalMode
from app.modules.rag.schemas import BM25SearchResult
from app.modules.rag.section_evidence_retriever import SectionEvidenceIndex


class FixedEmbeddings(LCEmbeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0, 0.0]


@pytest.mark.anyio
@pytest.mark.parametrize("mode", list(RetrievalMode))
@pytest.mark.parametrize(
    ("bula_id", "corpus", "expected_ids"),
    [
        (None, (BulaCorpus.SHARED, BulaCorpus.SYSTEM), {"chunk-2", "chunk-3"}),
        (UUID(int=2), (BulaCorpus.SYSTEM,), {"chunk-2"}),
        (UUID(int=1), (BulaCorpus.SYSTEM,), set()),
        (UUID(int=1), None, {"chunk-1"}),
        (None, (), set()),
    ],
)
async def test_factory_results_respect_bula_and_corpus_intersection(
    mode: RetrievalMode,
    bula_id: UUID | None,
    corpus: tuple[BulaCorpus, ...] | None,
    expected_ids: set[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedding_adapter = EmbeddingAdapter(embedder=FixedEmbeddings(), dimension=4)
    source_results = [
        BM25SearchResult(
            chunk_id=f"chunk-{number}",
            doc_id=str(UUID(int=number)),
            bula_id=UUID(int=number),
            corpus=source_corpus,
            drug_name=f"Produto {number}",
            section_title="Informações",
            chunk_text=f"Texto original da fonte {number}.",
            bm25_score=float(4 - number),
        )
        for number, source_corpus in enumerate(
            (BulaCorpus.PRIVATE, BulaCorpus.SYSTEM, BulaCorpus.SHARED), start=1
        )
    ]

    async def search_lexical_index(
        query: str,
        *,
        k: int,
        bula_id: UUID | None,
        corpus: tuple[BulaCorpus, ...] | None,
        include_administrative_sections: bool,
    ) -> list[BM25SearchResult]:
        return [
            result
            for result in source_results
            if (bula_id is None or result.bula_id == bula_id)
            and (corpus is None or result.corpus in corpus)
        ][:k]

    lexical_index = AsyncMock(spec=BM25SearchIndex)
    lexical_index.search.side_effect = search_lexical_index
    section_index = AsyncMock(spec=SectionEvidenceIndex)

    def build_embeddings(settings: Settings) -> EmbeddingAdapter:
        return embedding_adapter

    if mode != RetrievalMode.BM25:
        monkeypatch.setattr(dependencies, "get_embeddings", build_embeddings)

    client = AsyncQdrantClient(location=":memory:")
    try:
        store = QdrantVectorStore(client=client, vector_size=4)
        await store.ensure_collection()
        await store.upsert_points(
            [
                PointStruct(
                    id=make_point_id(result.chunk_id),
                    vector=[1.0, 0.0, 0.0, 0.0],
                    payload={
                        "chunk_id": result.chunk_id,
                        "bula_id": str(result.bula_id),
                        "corpus": result.corpus.value,
                        "chunk_text": result.chunk_text,
                        "section_title": result.section_title,
                        "drug_name": result.drug_name,
                        "manufacturer": f"Fabricante {result.bula_id.int}",
                        "embedding_profile": embedding_adapter.embedding_profile,
                    },
                )
                for result in source_results
            ]
        )
        application = FastAPI()
        # BM25 must also work without an app Qdrant client or embedding API key.
        if mode != RetrievalMode.BM25:
            setattr(application.state, QDRANT_CLIENT_STATE_KEY, client)
        factory = dependencies.get_retriever_strategy_factory(
            request=Request({"type": "http", "app": application}),
            settings=Settings(embedding={"dimension": 4}),
            bm25_factory=BM25RetrieverFactory(index=lexical_index),
            section_index=section_index,
        )
        retriever = factory.build(mode=mode, bula_id=bula_id, corpus=corpus, k=4)
        question = "Tenho alergia?" if bula_id is None else "Informações da fonte?"
        documents = await retriever.ainvoke(question)

        assert {document.metadata["chunk_id"] for document in documents} == expected_ids
        for document in documents:
            source = next(
                result
                for result in source_results
                if result.chunk_id == document.metadata["chunk_id"]
            )
            assert document.page_content == source.chunk_text
            assert document.metadata["bula_id"] == str(source.bula_id)
            assert document.metadata["corpus"] == source.corpus.value
            if mode == RetrievalMode.HYBRID:
                assert document.metadata["retrieval_sources"] == ["dense", "bm25"]
                assert document.metadata["manufacturer"] == (
                    f"Fabricante {source.bula_id.int}"
                )
        section_index.find_section_evidence.assert_not_awaited()
        if mode == RetrievalMode.DENSE or corpus == ():
            lexical_index.search.assert_not_awaited()
        else:
            lexical_index.search.assert_awaited_once_with(
                question,
                k=12 if mode == RetrievalMode.HYBRID else 4,
                bula_id=bula_id,
                corpus=corpus,
                include_administrative_sections=False,
            )
    finally:
        await client.close()
