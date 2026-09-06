import asyncio
import re
from typing import Any, Self

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, model_validator
from qdrant_client.models import FieldCondition, Filter, MatchValue, ScoredPoint

from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.qdrant_store import QdrantVectorStore


CITATION_METADATA_KEYS = ("section_title", "chunk_id", "drug_name", "bula_id")
EXTRA_PAYLOAD_METADATA_KEYS = ("chunk_index", "manufacturer", "corpus")
STRUCTURAL_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+.*$", re.MULTILINE)
DEFAULT_CANDIDATE_MULTIPLIER = 3
SYNC_RETRIEVER_ERROR = (
    "DenseBulaRetriever must be used via async path "
    "(ainvoke / _aget_relevant_documents)"
)


class DenseBulaRetriever(BaseRetriever):
    bula_id: str
    k: int = 4
    qdrant_store: QdrantVectorStore
    embeddings: EmbeddingAdapter
    candidate_multiplier: int = DEFAULT_CANDIDATE_MULTIPLIER

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def validate_k(self) -> Self:
        if self.k < 1:
            raise ValueError("k must be >= 1")

        if self.candidate_multiplier < 1:
            raise ValueError("candidate_multiplier must be >= 1")

        return self

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = run_manager
        query_vector = await asyncio.to_thread(self.embeddings.embed_query, query)
        search_result = await self.qdrant_store.search_similar(
            vector=query_vector,
            limit=self.k * self.candidate_multiplier,
            query_filter=self._build_bula_filter(),
        )
        evidence_documents: list[Document] = []
        for point in search_result.points:
            if point.payload is None:
                continue

            document = self._point_to_document(point)
            if not self._has_evidence_beyond_markdown_headings(document.page_content):
                continue

            evidence_documents.append(document)
            if len(evidence_documents) == self.k:
                break

        return evidence_documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        raise RuntimeError(SYNC_RETRIEVER_ERROR)

    def _build_bula_filter(self) -> Filter:
        return Filter(
            must=[
                FieldCondition(
                    key="bula_id",
                    match=MatchValue(value=self.bula_id),
                ),
                FieldCondition(
                    key="embedding_profile",
                    match=MatchValue(value=self.embeddings.embedding_profile),
                ),
            ]
        )

    def _point_to_document(self, point: ScoredPoint) -> Document:
        payload = point.payload or {}
        metadata = self._build_metadata(payload=payload, score=point.score)
        page_content = str(payload.get("chunk_text", ""))

        return Document(page_content=page_content, metadata=metadata)

    def _build_metadata(
        self,
        *,
        payload: dict[str, Any],
        score: float | None,
    ) -> dict[str, Any]:
        metadata = {
            key: payload[key]
            for key in (*CITATION_METADATA_KEYS, *EXTRA_PAYLOAD_METADATA_KEYS)
            if key in payload
        }

        if score is not None:
            metadata["score"] = score

        return metadata

    def _has_evidence_beyond_markdown_headings(self, chunk_text: str) -> bool:
        text_without_headings = STRUCTURAL_HEADING_PATTERN.sub("", chunk_text)
        return bool(text_without_headings.strip())
