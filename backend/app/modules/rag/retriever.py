import asyncio
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
SYNC_RETRIEVER_ERROR = (
    "DenseBulaRetriever must be used via async path "
    "(ainvoke / _aget_relevant_documents)"
)


class DenseBulaRetriever(BaseRetriever):
    bula_id: str
    k: int = 4
    qdrant_store: QdrantVectorStore
    embeddings: EmbeddingAdapter

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def validate_k(self) -> Self:
        if self.k < 1:
            raise ValueError("k must be >= 1")

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
            limit=self.k,
            query_filter=self._build_bula_filter(),
        )
        return [
            self._point_to_document(point)
            for point in search_result.points
            if point.payload is not None
        ]

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
                )
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
