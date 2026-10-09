import uuid
from collections.abc import Sequence
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    ExtendedPointId,
    Filter,
    FieldCondition,
    MatchValue,
    PointIdsList,
    PointStruct,
    QueryResponse,
    Record,
    VectorParams,
)

from app.modules.bulas.models import Bula, BulaCorpus
from app.modules.rag.schemas import DocumentChunk
from app.modules.rag.source_content import classify_chunk_content


SHARED_COLLECTION = "bulaai_chunks"


def make_point_id(chunk_id: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, chunk_id).hex


def build_qdrant_point(
    *,
    bula: Bula,
    chunk: DocumentChunk,
    vector: list[float],
    embedding_profile: str,
) -> PointStruct:
    corpus = (
        bula.corpus.value if isinstance(bula.corpus, BulaCorpus) else str(bula.corpus)
    )
    payload: dict[str, object] = {
        "bula_id": str(bula.id),
        "corpus": corpus,
        "drug_name": bula.drug_name,
        "manufacturer": bula.manufacturer,
        "section_title": chunk.section_title,
        "chunk_text": chunk.text,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.index,
        "embedding_profile": embedding_profile,
        "content_role": classify_chunk_content(chunk.text).value,
    }

    return PointStruct(
        id=make_point_id(chunk.chunk_id),
        vector=vector,
        payload=payload,
    )


class QdrantVectorStore:
    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str = SHARED_COLLECTION,
        vector_size: int = 1024,
    ) -> None:
        self._client = client
        self.collection_name = collection_name
        self.vector_size = vector_size

    async def ensure_collection(self) -> None:
        collection_exists = await self._client.collection_exists(self.collection_name)
        if collection_exists:
            return

        await self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    async def upsert_points(self, points: list[PointStruct]) -> int:
        if not points:
            return 0

        await self._client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        return len(points)

    async def replace_bula_points(
        self, *, bula_id: str, points: list[PointStruct]
    ) -> int:
        """Replace one bula's points and verify that no obsolete points remain.

        The caller must keep the bula unavailable until this method and the
        PostgreSQL replacement have both completed. Retrying is safe because
        point IDs are deterministic for each chunk identity.
        """
        if not bula_id.strip() or not points:
            raise ValueError("A bula ID and nonempty point set are required.")

        expected_point_ids: set[str] = set()
        for point in points:
            if (
                not isinstance(point.payload, dict)
                or point.payload.get("bula_id") != bula_id
            ):
                raise ValueError("Replacement points must belong to the selected bula.")
            expected_point_ids.add(self._normalize_point_id(point.id))
        if len(expected_point_ids) != len(points):
            raise ValueError("Replacement points contain duplicate identities.")

        await self.upsert_points(points)
        current_points = await self.list_points_for_bula(bula_id=bula_id)
        obsolete_point_ids: list[ExtendedPointId] = []
        for current_point in current_points:
            if (
                current_point.payload is None
                or current_point.payload.get("bula_id") != bula_id
            ):
                raise ValueError("Qdrant returned a point outside the selected bula.")
            if self._normalize_point_id(current_point.id) not in expected_point_ids:
                obsolete_point_ids.append(current_point.id)

        if obsolete_point_ids:
            await self._client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=obsolete_point_ids),
                wait=True,
            )

        remaining_points = await self.list_points_for_bula(bula_id=bula_id)
        remaining_ids = {
            self._normalize_point_id(point.id) for point in remaining_points
        }
        if remaining_ids != expected_point_ids or len(remaining_points) != len(points):
            raise RuntimeError(
                "Qdrant bula replacement did not match the expected chunks."
            )
        return len(points)

    @staticmethod
    def _normalize_point_id(point_id: ExtendedPointId) -> str:
        return str(point_id).replace("-", "").lower()

    async def search_similar(
        self,
        *,
        vector: list[float],
        limit: int = 5,
        query_filter: Filter | None = None,
    ) -> QueryResponse:
        return await self._client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    async def retrieve_payloads_by_chunk_ids(
        self,
        chunk_ids: Sequence[str],
    ) -> dict[str, dict[str, Any]]:
        unique_chunk_ids = list(dict.fromkeys(chunk_ids))
        if not unique_chunk_ids:
            return {}
        if any(not chunk_id.strip() for chunk_id in unique_chunk_ids):
            raise ValueError("Chunk identities must not be blank.")

        logical_id_by_point_id = {
            make_point_id(chunk_id): chunk_id for chunk_id in unique_chunk_ids
        }
        records = await self._client.retrieve(
            collection_name=self.collection_name,
            ids=list(logical_id_by_point_id),
            with_payload=True,
            with_vectors=False,
        )
        payloads_by_chunk_id: dict[str, dict[str, Any]] = {}
        for record in records:
            point_id = str(record.id).replace("-", "").lower()
            expected_chunk_id = logical_id_by_point_id.get(point_id)
            if expected_chunk_id is None:
                raise ValueError("Qdrant returned an unexpected point identity.")
            if record.payload is None:
                continue

            payload = dict(record.payload)
            payload_chunk_id = payload.get("chunk_id")
            if payload_chunk_id != expected_chunk_id:
                raise ValueError("Qdrant point and payload identities do not match.")
            if expected_chunk_id in payloads_by_chunk_id:
                raise ValueError("Qdrant returned a duplicate chunk payload.")
            payloads_by_chunk_id[expected_chunk_id] = payload

        return payloads_by_chunk_id

    async def list_points_for_bula(
        self,
        *,
        bula_id: str,
        page_size: int = 100,
    ) -> list[Record]:
        if page_size < 1:
            raise ValueError("page_size must be greater than zero.")

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="bula_id",
                    match=MatchValue(value=bula_id),
                )
            ]
        )
        records: list[Record] = []
        next_page_offset: ExtendedPointId | None = None

        while True:
            page_records, next_page_offset = await self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=page_size,
                offset=next_page_offset,
                with_payload=True,
                with_vectors=False,
            )
            records.extend(page_records)
            if next_page_offset is None:
                return records

    async def close(self) -> None:
        await self._client.close()
