from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.modules.rag.enriching_retriever import EnrichingRetriever
from app.modules.rag.hybrid_retriever import HybridRetrieverContractError


class StaticRetriever(BaseRetriever):
    documents: list[Document]

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        return self.documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        raise RuntimeError("StaticRetriever requires async ainvoke().")


class RecordingPayloadStore:
    payloads: dict[str, dict[str, Any]]
    received_chunk_ids: list[list[str]]

    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self.payloads = payloads
        self.received_chunk_ids = []

    async def retrieve_payloads_by_chunk_ids(
        self,
        chunk_ids: Sequence[str],
    ) -> dict[str, dict[str, Any]]:
        self.received_chunk_ids.append(list(chunk_ids))
        return {
            chunk_id: self.payloads[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in self.payloads
        }


def make_document(
    chunk_id: str | None,
    *,
    content: str = "Trecho da bula.",
    **metadata: object,
) -> Document:
    document_metadata = dict(metadata)
    if chunk_id is not None:
        document_metadata["chunk_id"] = chunk_id
    return Document(
        id=chunk_id,
        page_content=content,
        metadata=document_metadata,
    )


@pytest.mark.anyio
async def test_enricher_batches_payloads_and_preserves_result_order() -> None:
    first = make_document(
        "first",
        section_title="Posologia",
        score=0.03,
        rrf_score=0.03,
    )
    second = make_document("second", score=0.02, rrf_score=0.02)
    payload_store = RecordingPayloadStore(
        {
            "first": {
                "chunk_id": "first",
                "chunk_text": "Trecho da bula.",
                "drug_name": "Dipirona",
                "manufacturer": "Sanofi",
                "section_title": "Posologia",
                "bula_id": "bula-1",
                "corpus": "system",
                "embedding_profile": "must-not-leak",
            },
            "second": {
                "chunk_id": "second",
                "chunk_text": "Trecho da bula.",
                "drug_name": "Dipirona",
                "manufacturer": "Sanofi",
                "section_title": "Advertencias",
                "bula_id": "bula-1",
                "corpus": "system",
            },
        }
    )
    retriever = EnrichingRetriever(
        wrapped_retriever=StaticRetriever(documents=[first, second]),
        payload_store=payload_store,
    )

    documents = await retriever.ainvoke("pergunta")

    assert [document.id for document in documents] == ["first", "second"]
    assert payload_store.received_chunk_ids == [["first", "second"]]
    assert documents[0].metadata == {
        "chunk_id": "first",
        "section_title": "Posologia",
        "score": 0.03,
        "rrf_score": 0.03,
        "drug_name": "Dipirona",
        "manufacturer": "Sanofi",
        "bula_id": "bula-1",
        "corpus": "system",
    }
    assert documents[1].metadata["section_title"] == "Advertencias"
    assert "embedding_profile" not in documents[0].metadata


@pytest.mark.anyio
async def test_enricher_preserves_documents_missing_from_qdrant() -> None:
    original = make_document("missing", score=0.03)
    retriever = EnrichingRetriever(
        wrapped_retriever=StaticRetriever(documents=[original]),
        payload_store=RecordingPayloadStore({}),
    )

    documents = await retriever.ainvoke("pergunta")

    assert documents == [original]
    assert documents[0] is not original


@pytest.mark.anyio
async def test_enricher_does_not_access_qdrant_for_empty_results() -> None:
    payload_store = RecordingPayloadStore({})
    retriever = EnrichingRetriever(
        wrapped_retriever=StaticRetriever(documents=[]),
        payload_store=payload_store,
    )

    assert await retriever.ainvoke("pergunta") == []
    assert payload_store.received_chunk_ids == []


@pytest.mark.anyio
async def test_enricher_rejects_missing_chunk_identity() -> None:
    retriever = EnrichingRetriever(
        wrapped_retriever=StaticRetriever(documents=[make_document(None)]),
        payload_store=RecordingPayloadStore({}),
    )

    with pytest.raises(HybridRetrieverContractError, match="chunk identity"):
        await retriever.ainvoke("pergunta")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {
            "chunk_id": "other",
            "chunk_text": "Trecho da bula.",
        },
        {
            "chunk_id": "chunk-1",
            "chunk_text": "Outro trecho.",
        },
        {
            "chunk_id": "chunk-1",
            "chunk_text": "Trecho da bula.",
            "section_title": "Titulo divergente",
        },
    ],
)
async def test_enricher_rejects_inconsistent_payloads(
    payload: dict[str, Any],
) -> None:
    retriever = EnrichingRetriever(
        wrapped_retriever=StaticRetriever(
            documents=[make_document("chunk-1", section_title="Posologia")]
        ),
        payload_store=RecordingPayloadStore({"chunk-1": payload}),
    )

    with pytest.raises(HybridRetrieverContractError, match="disagree|identity"):
        await retriever.ainvoke("pergunta")


@pytest.mark.anyio
async def test_enricher_propagates_payload_store_failures() -> None:
    class FailingPayloadStore:
        async def retrieve_payloads_by_chunk_ids(
            self,
            chunk_ids: Sequence[str],
        ) -> dict[str, dict[str, Any]]:
            _ = chunk_ids
            raise TimeoutError("Qdrant unavailable")

    retriever = EnrichingRetriever(
        wrapped_retriever=StaticRetriever(documents=[make_document("chunk-1")]),
        payload_store=FailingPayloadStore(),
    )

    with pytest.raises(TimeoutError, match="Qdrant unavailable"):
        await retriever.ainvoke("pergunta")
