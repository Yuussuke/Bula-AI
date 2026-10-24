"""Filters apply before the vector Top-K and metadata never becomes evidence."""

from uuid import UUID
from unittest.mock import AsyncMock
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from app.modules.rag.published_evidence import (
    PublishedEvidenceIndex,
    PublishedEvidenceRetriever,
    document_identity,
)

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


def test_missing_identity_has_no_dangling_separator() -> None:
    document = Document(
        page_content="Texto.",
        metadata={"cross_bula": True, "drug_name": "", "manufacturer": None},
    )
    assert document_identity(document) == ""


class EmptySourceRetriever(BaseRetriever):
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return []


class RetrievalTrace(BaseCallbackHandler):
    def __init__(self) -> None:
        self.runs: list[tuple[UUID, UUID | None]] = []

    def on_retriever_start(
        self,
        serialized: dict[str, object],
        query: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        self.runs.append((run_id, parent_run_id))


@pytest.mark.anyio
async def test_internal_retrieval_trace_is_a_child_of_source_validation() -> None:
    trace = RetrievalTrace()
    index = AsyncMock(spec=PublishedEvidenceIndex)
    index.get_source_chunks.return_value = []
    retriever = PublishedEvidenceRetriever(
        wrapped_retriever=EmptySourceRetriever(),
        source_index=index,
        sources={UUID(int=1): {"drug_name": "Produto"}},
    )
    assert await retriever.ainvoke("Pergunta", config={"callbacks": [trace]}) == []
    assert len(trace.runs) == 2
    assert trace.runs[0][1] is None
    assert trace.runs[1][1] == trace.runs[0][0]


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
        "[E1] Fonte 1; medicamento: Produto A; fabricante: Fabricante A; apresentação: gotas; seção:"
        in formatted
    )
    assert (
        "[E2] Fonte 2; medicamento: Produto B; fabricante: Fabricante B; apresentação: comprimidos; seção:"
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
