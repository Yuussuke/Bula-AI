import re
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from qdrant_client.models import Filter, ScoredPoint

from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.retriever import DenseBulaRetriever, SYNC_RETRIEVER_ERROR


class FakeEmbeddings(LCEmbeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [1.0, 0.0, 0.0, 0.0]


class FakeQdrantStore(QdrantVectorStore):
    def __init__(self, *, points: list[ScoredPoint] | None = None) -> None:
        self.query_filter: Filter | None = None
        self.requested_limit: int | None = None
        self.collection_name = "fake_collection"
        self.vector_size = 4
        self.points = points or [build_scored_point()]

    async def search_similar(
        self,
        *,
        vector: list[float],
        limit: int = 5,
        query_filter: Filter | None = None,
    ) -> SimpleNamespace:
        _ = vector
        self.requested_limit = limit
        self.query_filter = query_filter
        return SimpleNamespace(points=self.points)


def build_scored_point(
    *,
    point_id: str = "point-1",
    chunk_id: str = "chunk-1",
    chunk_text: str = "Dose usual: 1 comprimido.",
    score: float = 0.93,
) -> ScoredPoint:
    return ScoredPoint(
        id=point_id,
        version=0,
        score=score,
        payload={
            "bula_id": "bula-123",
            "chunk_id": chunk_id,
            "chunk_text": chunk_text,
            "drug_name": "Dipirona",
            "section_title": "Posologia",
            "chunk_index": 0,
            "manufacturer": "Example Pharma",
            "corpus": "private",
            "embedding_profile": "unspecified;input=plain-v1",
        },
    )


def build_embedding_adapter() -> EmbeddingAdapter:
    return EmbeddingAdapter(
        embedder=FakeEmbeddings(),
        batch_size=1,
        dimension=4,
    )


@pytest.mark.anyio
async def test_retriever_returns_section_metadata() -> None:
    qdrant_store = FakeQdrantStore()
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=qdrant_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Como tomar?")

    assert len(documents) == 1
    assert documents[0].page_content == "Dose usual: 1 comprimido."
    assert documents[0].metadata == {
        "section_title": "Posologia",
        "chunk_id": "chunk-1",
        "drug_name": "Dipirona",
        "bula_id": "bula-123",
        "chunk_index": 0,
        "manufacturer": "Example Pharma",
        "corpus": "private",
        "score": 0.93,
    }
    assert qdrant_store.requested_limit == 12
    assert qdrant_store.query_filter is not None
    assert len(qdrant_store.query_filter.must or []) == 2


@pytest.mark.anyio
async def test_retriever_skips_heading_only_candidates() -> None:
    qdrant_store = FakeQdrantStore(
        points=[
            build_scored_point(
                point_id="heading-point",
                chunk_id="heading-chunk",
                chunk_text="## INFORMACOES AO PACIENTE",
                score=0.98,
            ),
            build_scored_point(
                point_id="evidence-point",
                chunk_id="evidence-chunk",
                chunk_text=(
                    "## ADVERTENCIAS\n"
                    "Este medicamento contem acucar e requer orientacao profissional."
                ),
                score=0.91,
            ),
        ]
    )
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=qdrant_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Pode ser usado por pessoas com diabetes?")

    assert [document.metadata["chunk_id"] for document in documents] == [
        "evidence-chunk"
    ]


def test_retriever_rejects_invalid_candidate_multiplier() -> None:
    with pytest.raises(ValueError, match="candidate_multiplier must be >= 1"):
        DenseBulaRetriever(
            bula_id="bula-123",
            candidate_multiplier=0,
            qdrant_store=FakeQdrantStore(),
            embeddings=build_embedding_adapter(),
        )


def test_retriever_rejects_invalid_k() -> None:
    with pytest.raises(ValueError, match="k must be >= 1"):
        DenseBulaRetriever(
            bula_id="bula-123",
            k=0,
            qdrant_store=FakeQdrantStore(),
            embeddings=build_embedding_adapter(),
        )


def test_retriever_sync_path_rejects_direct_use() -> None:
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=FakeQdrantStore(),
        embeddings=build_embedding_adapter(),
    )

    with pytest.raises(RuntimeError, match=re.escape(SYNC_RETRIEVER_ERROR)):
        retriever.invoke("Como tomar?")
