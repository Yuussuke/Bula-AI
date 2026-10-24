"""Canonical source validation inside the authorized cross-bula retrieval boundary."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

import structlog

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.modules.rag.schemas import ChunkMetadataInput
from app.modules.rag.source_content import without_front_matter

logger = structlog.get_logger(__name__)


@runtime_checkable
class PublishedEvidenceIndex(Protocol):
    async def get_source_chunks(
        self, *, chunk_ids: Sequence[str], bula_ids: Sequence[UUID]
    ) -> list[ChunkMetadataInput]: ...


class PublishedEvidenceRetriever(BaseRetriever):
    wrapped_retriever: BaseRetriever
    source_index: PublishedEvidenceIndex = Field(exclude=True, repr=False)
    sources: dict[UUID, dict[str, str]]
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        if not self.sources:
            return []
        documents = await self.wrapped_retriever.ainvoke(
            query, config={"callbacks": run_manager.get_child()}
        )
        chunks = await self.source_index.get_source_chunks(
            chunk_ids=[
                str(document.metadata.get("chunk_id", "")) for document in documents
            ],
            bula_ids=list(self.sources),
        )
        canonical_chunks = {chunk.chunk_id: chunk for chunk in chunks}
        validated_documents: list[Document] = []
        for document in documents:
            chunk_id = str(document.metadata.get("chunk_id", ""))
            chunk = canonical_chunks.get(chunk_id)
            if chunk is None or chunk.bula_id not in self.sources:
                continue
            if chunk.doc_id != str(chunk.bula_id) or chunk.corpus.value != "system":
                continue
            if str(document.metadata.get("bula_id", "")) != str(chunk.bula_id):
                continue
            if document.metadata.get("corpus") != "system":
                continue
            if without_front_matter(document.page_content) != without_front_matter(
                chunk.chunk_text
            ):
                continue
            if document.metadata.get("section_title") != chunk.section_title:
                continue
            metadata = dict(document.metadata)
            metadata.update(self.sources[chunk.bula_id])
            metadata.update(
                chunk_id=chunk_id, bula_id=str(chunk.bula_id), cross_bula=True
            )
            validated_documents.append(
                Document(page_content=chunk.chunk_text, metadata=metadata)
            )
        logger.info(
            "rag_published_source_validation",
            candidate_count=len(documents),
            validated_count=len(validated_documents),
            discarded_count=len(documents) - len(validated_documents),
        )
        return validated_documents

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        raise RuntimeError("PublishedEvidenceRetriever requires async ainvoke().")


def document_identity(document: Document) -> str:
    """Source labels are identification, never additional medical evidence."""
    if not document.metadata.get("cross_bula"):
        return ""
    labels = {
        "drug_name": "medicamento",
        "manufacturer": "fabricante",
        "presentation": "apresentação",
        "strength": "concentração",
    }
    identity = "; ".join(
        f"{label}: {document.metadata[key]}"
        for key, label in labels.items()
        if document.metadata.get(key)
    )
    return f"{identity}; " if identity else ""
