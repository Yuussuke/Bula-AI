"""Metadata enrichment decorator for retrieved source documents."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.modules.rag.hybrid_retriever import HybridRetrieverContractError


ENRICHED_METADATA_KEYS = (
    "drug_name",
    "manufacturer",
    "section_title",
    "bula_id",
    "corpus",
)


@runtime_checkable
class ChunkPayloadStore(Protocol):
    async def retrieve_payloads_by_chunk_ids(
        self,
        chunk_ids: Sequence[str],
    ) -> dict[str, dict[str, Any]]: ...


class EnrichingRetriever(BaseRetriever):
    """Decorate final retrieval results with allowlisted Qdrant metadata."""

    wrapped_retriever: BaseRetriever = Field(exclude=True, repr=False)
    payload_store: ChunkPayloadStore = Field(exclude=True, repr=False)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        documents = await self.wrapped_retriever.ainvoke(
            query,
            config={"callbacks": run_manager.get_child(tag="wrapped_retriever")},
        )
        if not documents:
            return []

        chunk_ids = [self._get_chunk_id(document) for document in documents]
        payloads_by_chunk_id = await self.payload_store.retrieve_payloads_by_chunk_ids(
            chunk_ids
        )
        return [
            self._enrich_document(
                document=document,
                payload=payloads_by_chunk_id.get(chunk_id),
            )
            for document, chunk_id in zip(documents, chunk_ids, strict=True)
        ]

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        raise RuntimeError("EnrichingRetriever requires async ainvoke().")

    def _get_chunk_id(self, document: Document) -> str:
        chunk_id = document.metadata.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise HybridRetrieverContractError(
                "A retrieved document is missing a valid chunk identity."
            )
        return chunk_id

    def _enrich_document(
        self,
        *,
        document: Document,
        payload: dict[str, Any] | None,
    ) -> Document:
        enriched_document = document.model_copy(deep=True)
        if payload is None:
            return enriched_document

        payload_chunk_id = payload.get("chunk_id")
        if payload_chunk_id != self._get_chunk_id(document):
            raise HybridRetrieverContractError(
                "Qdrant payload identity does not match the retrieved chunk."
            )

        payload_text = payload.get("chunk_text")
        if isinstance(payload_text, str) and payload_text != document.page_content:
            raise HybridRetrieverContractError(
                "Qdrant and fused retrieval disagree on chunk source text."
            )

        for key in ENRICHED_METADATA_KEYS:
            incoming_value = payload.get(key)
            if self._is_missing_metadata(incoming_value):
                continue

            existing_value = enriched_document.metadata.get(key)
            if self._is_missing_metadata(existing_value):
                enriched_document.metadata[key] = incoming_value
                continue
            if existing_value != incoming_value:
                raise HybridRetrieverContractError(
                    "Qdrant and fused retrieval disagree on chunk metadata."
                )

        return enriched_document

    def _is_missing_metadata(self, value: Any) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())
