from uuid import UUID

from pgqueuer.queries import Queries


INGEST_BULA_ENTRYPOINT = "ingest_bula"


class BulaIngestionQueue:
    def __init__(self, queries: Queries) -> None:
        self.queries = queries

    async def enqueue_bula_ingestion(
        self, *, bula_id: UUID, dedupe_key: str | None = None
    ) -> None:
        payload = str(bula_id).encode()
        if dedupe_key is not None:
            await self.queries.enqueue(
                INGEST_BULA_ENTRYPOINT, payload, priority=0, dedupe_key=dedupe_key
            )
            return
        await self.queries.enqueue(
            INGEST_BULA_ENTRYPOINT,
            payload,
            priority=0,
        )
