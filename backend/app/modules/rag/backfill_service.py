from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from qdrant_client.models import Record
import structlog

from app.modules.bulas.models import Bula, BulaStatus
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.bm25_index import PostgreSQLBM25Index
from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id
from app.modules.rag.schemas import ChunkMetadataInput

logger = structlog.get_logger(__name__)


class ChunkBackfillError(ValueError):
    """Existing source chunks are not safe to copy into the lexical index."""


@dataclass(frozen=True)
class ChunkBackfillResult:
    bula_count: int
    chunk_count: int
    is_dry_run: bool


class ChunkMetadataBackfillService:
    def __init__(
        self,
        *,
        bula_repository: BulaRepository,
        qdrant_store: QdrantVectorStore,
        bm25_index: PostgreSQLBM25Index,
    ) -> None:
        self.bula_repository = bula_repository
        self.qdrant_store = qdrant_store
        self.bm25_index = bm25_index

    async def backfill(
        self,
        *,
        bula_id: UUID | None = None,
        batch_size: int = 100,
        is_dry_run: bool = False,
    ) -> ChunkBackfillResult:
        if not 1 <= batch_size <= 1000:
            raise ChunkBackfillError("batch_size must be between 1 and 1000.")
        bula_count = 0
        chunk_count = 0
        async for bula in self._selected_bulas(bula_id=bula_id, batch_size=batch_size):
            records = await self.qdrant_store.list_points_for_bula(
                bula_id=str(bula.id), page_size=batch_size
            )
            if not records:
                raise ChunkBackfillError(f"No Qdrant chunks found for bula {bula.id}.")
            # Validate the entire document BEFORE replacing any of its index.
            chunks = [
                self._convert_record(bula=bula, record=record) for record in records
            ]
            if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
                raise ChunkBackfillError(
                    f"Duplicate chunk identities for bula {bula.id}."
                )
            if not is_dry_run:
                await self.bm25_index.replace_bula_chunks(
                    bula_id=bula.id, chunks=chunks
                )
            bula_count += 1
            chunk_count += len(chunks)
            logger.info(
                "chunk_metadata_backfill_bula_finished",
                bula_id=str(bula.id),
                chunk_count=len(chunks),
                completed_bula_count=bula_count,
                is_dry_run=is_dry_run,
            )
        return ChunkBackfillResult(bula_count, chunk_count, is_dry_run)

    async def _selected_bulas(
        self, *, bula_id: UUID | None, batch_size: int
    ) -> AsyncIterator[Bula]:
        if bula_id is not None:
            bula = await self.bula_repository.get_by_id(bula_id=bula_id)
            if bula is None or bula.status != BulaStatus.READY:
                raise ChunkBackfillError("Select an existing ready bula for backfill.")
            yield bula
            return
        after_id: UUID | None = None
        while True:
            bulas = await self.bula_repository.list_ready_bulas_for_indexing(
                after_id=after_id, limit=batch_size
            )
            if not bulas:
                return
            for bula in bulas:
                yield bula
            after_id = bulas[-1].id

    def _convert_record(self, *, bula: Bula, record: Record) -> ChunkMetadataInput:
        payload = record.payload or {}
        chunk_id = payload.get("chunk_id")
        chunk_text = payload.get("chunk_text")
        section_title = payload.get("section_title")
        if (
            payload.get("bula_id") != str(bula.id)
            or payload.get("doc_id", str(bula.id)) != str(bula.id)
            or not isinstance(chunk_id, str)
            or not chunk_id.strip()
            or not isinstance(chunk_text, str)
            or not chunk_text.strip()
            or not isinstance(section_title, str)
        ):
            raise ChunkBackfillError(
                f"Invalid source metadata at Qdrant point {record.id}."
            )
        try:
            has_matching_identity = UUID(str(record.id)) == UUID(
                make_point_id(chunk_id)
            )
        except ValueError:
            has_matching_identity = False
        if not has_matching_identity:
            raise ChunkBackfillError(f"Chunk/point identity mismatch at {record.id}.")
        # Current PostgreSQL metadata wins over potentially stale Qdrant metadata.
        # Historical payloads do not carry doc_id; the application's document ID
        # is the bula UUID. Preserve chunk_id, never substitute the point UUID.
        return ChunkMetadataInput(
            chunk_id=chunk_id,
            doc_id=str(bula.id),
            bula_id=bula.id,
            corpus=bula.corpus,
            drug_name=bula.drug_name,
            section_title=section_title,
            chunk_text=chunk_text,
        )
