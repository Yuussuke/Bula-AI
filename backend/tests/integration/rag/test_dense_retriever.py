import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from langchain_core.retrievers import BaseRetriever
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.modules.rag.dependencies import get_dense_retriever
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id
from app.modules.rag.retriever import DenseBulaRetriever


TEST_EMBEDDING_PROFILE = "unspecified;input=plain-v1"


class RecordingEmbeddings(LCEmbeddings):
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        _ = texts
        return []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [1.0, 0.0, 0.0, 0.0]


def build_retriever_point(
    *,
    chunk_id: str,
    bula_id: str,
    chunk_text: str,
    vector: list[float] | None = None,
    embedding_profile: str = TEST_EMBEDDING_PROFILE,
) -> PointStruct:
    return PointStruct(
        id=make_point_id(chunk_id),
        vector=vector or [1.0, 0.0, 0.0, 0.0],
        payload={
            "bula_id": bula_id,
            "chunk_id": chunk_id,
            "chunk_text": chunk_text,
            "drug_name": "Dipirona",
            "section_title": "Posologia",
            "chunk_index": 0,
            "manufacturer": "Example Pharma",
            "corpus": "private",
            "embedding_profile": embedding_profile,
        },
    )


def build_embedding_adapter(
    recording_embeddings: RecordingEmbeddings | None = None,
) -> EmbeddingAdapter:
    return EmbeddingAdapter(
        embedder=recording_embeddings or RecordingEmbeddings(),
        batch_size=1,
        dimension=4,
    )


@pytest.mark.anyio
async def test_retriever_filters_by_bula_id(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, _, _ = qdrant_test_context
    await vector_store.ensure_collection()
    await vector_store.upsert_points(
        [
            build_retriever_point(
                chunk_id="allowed-chunk",
                bula_id="allowed-bula",
                chunk_text="Conteudo permitido.",
            ),
            build_retriever_point(
                chunk_id="blocked-chunk",
                bula_id="blocked-bula",
                chunk_text="Conteudo de outra bula.",
            ),
        ]
    )
    retriever = DenseBulaRetriever(
        bula_id="allowed-bula",
        qdrant_store=vector_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Como tomar?")

    assert [document.metadata["bula_id"] for document in documents] == ["allowed-bula"]
    assert [document.metadata["chunk_id"] for document in documents] == [
        "allowed-chunk"
    ]


@pytest.mark.anyio
async def test_retriever_excludes_points_from_an_incompatible_embedding_profile(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, _, _ = qdrant_test_context
    await vector_store.ensure_collection()
    await vector_store.upsert_points(
        [
            build_retriever_point(
                chunk_id="current-profile",
                bula_id="profile-bula",
                chunk_text="Conteudo com o perfil atual.",
            ),
            build_retriever_point(
                chunk_id="legacy-profile",
                bula_id="profile-bula",
                chunk_text="Conteudo vetorizado pelo contrato anterior.",
                embedding_profile="legacy-profile",
            ),
        ]
    )
    retriever = DenseBulaRetriever(
        bula_id="profile-bula",
        qdrant_store=vector_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Qual e o conteudo?")

    assert [document.metadata["chunk_id"] for document in documents] == [
        "current-profile"
    ]


@pytest.mark.anyio
async def test_retriever_respects_top_k(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, _, _ = qdrant_test_context
    await vector_store.ensure_collection()
    await vector_store.upsert_points(
        [
            build_retriever_point(
                chunk_id=f"chunk-{index}",
                bula_id="bula-top-k",
                chunk_text=f"Chunk {index}",
            )
            for index in range(5)
        ]
    )
    retriever = DenseBulaRetriever(
        bula_id="bula-top-k",
        k=2,
        qdrant_store=vector_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Como tomar?")

    assert len(documents) == 2


@pytest.mark.anyio
async def test_retriever_empty_results_no_crash(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, _, _ = qdrant_test_context
    await vector_store.ensure_collection()
    retriever = DenseBulaRetriever(
        bula_id="missing-bula",
        qdrant_store=vector_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Como tomar?")

    assert documents == []


@pytest.mark.anyio
async def test_retriever_same_embedding_as_ingestion(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, _, _ = qdrant_test_context
    await vector_store.ensure_collection()
    await vector_store.upsert_points(
        [
            build_retriever_point(
                chunk_id="embedding-chunk",
                bula_id="embedding-bula",
                chunk_text="Texto recuperado.",
            )
        ]
    )
    recording_embeddings = RecordingEmbeddings()
    embedding_adapter = build_embedding_adapter(recording_embeddings)

    retriever = get_dense_retriever(
        bula_id="embedding-bula",
        k=1,
        qdrant_store=vector_store,
        embeddings=embedding_adapter,
    )
    documents = await retriever.ainvoke("Pergunta do usuario")

    assert isinstance(retriever, BaseRetriever)
    assert isinstance(retriever, DenseBulaRetriever)
    assert retriever.embeddings is embedding_adapter
    assert recording_embeddings.queries == ["Pergunta do usuario"]
    assert documents[0].page_content == "Texto recuperado."
