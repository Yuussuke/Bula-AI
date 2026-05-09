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
    def __init__(self) -> None:
        self.query_filter: Filter | None = None
        self.collection_name = "fake_collection"
        self.vector_size = 4

    async def search_similar(
        self,
        *,
        vector: list[float],
        limit: int = 5,
        query_filter: Filter | None = None,
    ) -> SimpleNamespace:
        _ = vector
        _ = limit
        self.query_filter = query_filter
        return SimpleNamespace(
            points=[
                ScoredPoint(
                    id="point-1",
                    version=0,
                    score=0.93,
                    payload={
                        "bula_id": "bula-123",
                        "chunk_id": "chunk-1",
                        "chunk_text": "Dose usual: 1 comprimido.",
                        "drug_name": "Dipirona",
                        "section_title": "Posologia",
                        "chunk_index": 0,
                        "manufacturer": "Example Pharma",
                        "corpus": "private",
                    },
                )
            ]
        )


def build_embedding_adapter() -> EmbeddingAdapter:
    return EmbeddingAdapter(
        embedder=FakeEmbeddings(),
        batch_size=1,
        dimension=4,
    )


@pytest.mark.anyio
async def test_retriever_returns_section_metadata() -> None:
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=FakeQdrantStore(),
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
