from __future__ import annotations

import asyncio
from dataclasses import dataclass

from qdrant_client.models import PointStruct, Record

from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.qdrant_store import QdrantVectorStore


class DenseEmbeddingReindexError(Exception):
    """Raised when existing Qdrant chunks cannot be safely re-embedded."""


@dataclass(frozen=True)
class DenseEmbeddingReindexResult:
    bula_id: str
    point_count: int
    embedding_profile: str
    is_dry_run: bool


class DenseEmbeddingReindexService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingAdapter,
        qdrant_store: QdrantVectorStore,
    ) -> None:
        self.embeddings = embeddings
        self.qdrant_store = qdrant_store

    async def reindex_bula(
        self,
        *,
        bula_id: str,
        is_dry_run: bool = False,
    ) -> DenseEmbeddingReindexResult:
        clean_bula_id = bula_id.strip()
        if not clean_bula_id:
            raise DenseEmbeddingReindexError("A bula identifier is required.")

        existing_points = await self.qdrant_store.list_points_for_bula(
            bula_id=clean_bula_id,
        )
        if not existing_points:
            raise DenseEmbeddingReindexError(
                "No existing Qdrant chunks were found for this bula."
            )

        chunk_texts = [self._get_chunk_text(point=point) for point in existing_points]
        if is_dry_run:
            return self._build_result(
                bula_id=clean_bula_id,
                point_count=len(existing_points),
                is_dry_run=True,
            )

        vectors = await asyncio.to_thread(
            self.embeddings.embed_documents,
            chunk_texts,
        )
        reindexed_points = [
            self._build_reindexed_point(point=point, vector=vector)
            for point, vector in zip(existing_points, vectors, strict=True)
        ]
        point_count = await self.qdrant_store.upsert_points(reindexed_points)
        return self._build_result(
            bula_id=clean_bula_id,
            point_count=point_count,
            is_dry_run=False,
        )

    def _get_chunk_text(self, *, point: Record) -> str:
        payload = point.payload
        if payload is None:
            raise DenseEmbeddingReindexError(
                f"Qdrant point {point.id} does not contain a payload."
            )

        chunk_text = str(payload.get("chunk_text", "")).strip()
        if not chunk_text:
            raise DenseEmbeddingReindexError(
                f"Qdrant point {point.id} does not contain chunk_text."
            )

        return chunk_text

    def _build_reindexed_point(
        self,
        *,
        point: Record,
        vector: list[float],
    ) -> PointStruct:
        payload = dict(point.payload or {})
        payload["embedding_profile"] = self.embeddings.embedding_profile
        return PointStruct(
            id=point.id,
            vector=vector,
            payload=payload,
        )

    def _build_result(
        self,
        *,
        bula_id: str,
        point_count: int,
        is_dry_run: bool,
    ) -> DenseEmbeddingReindexResult:
        return DenseEmbeddingReindexResult(
            bula_id=bula_id,
            point_count=point_count,
            embedding_profile=self.embeddings.embedding_profile,
            is_dry_run=is_dry_run,
        )
