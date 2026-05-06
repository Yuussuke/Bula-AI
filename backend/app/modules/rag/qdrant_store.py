import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, QueryResponse, VectorParams

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
    ) -> QueryResponse:
        return await self._client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
        )

    async def close(self) -> None:
        await self._client.close()
