import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    ExtendedPointId,
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
    QueryResponse,
    Record,
    VectorParams,
)

from app.modules.bulas.models import Bula, BulaCorpus
from app.modules.rag.schemas import DocumentChunk


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
