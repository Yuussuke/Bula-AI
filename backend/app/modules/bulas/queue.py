from uuid import UUID

from pgqueuer.queries import Queries


INGEST_BULA_ENTRYPOINT = "ingest_bula"


class BulaIngestionQueue:
    def __init__(self, queries: Queries) -> None:
        self.queries = queries

    async def enqueue_bula_ingestion(self, *, bula_id: UUID) -> None:
        payload = str(bula_id).encode()
        await self.queries.enqueue(
            INGEST_BULA_ENTRYPOINT,
            payload,
            priority=0,
        )
