from uuid import UUID

import pytest

from app.modules.bulas.queue import BulaIngestionQueue, INGEST_BULA_ENTRYPOINT


class FakeQueries:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, int]] = []

    async def enqueue(
        self,
        entrypoint: str,
        payload: bytes,
        priority: int,
    ) -> list[object]:
        self.calls.append((entrypoint, payload, priority))
        return []


@pytest.mark.anyio
async def test_enqueue_bula_ingestion_uses_expected_entrypoint_and_payload() -> None:
    queries = FakeQueries()
    queue = BulaIngestionQueue(queries=queries)  # type: ignore[arg-type]
    bula_id = UUID("11111111-1111-1111-1111-111111111111")

    await queue.enqueue_bula_ingestion(bula_id=bula_id)

    assert queries.calls == [
        (INGEST_BULA_ENTRYPOINT, b"11111111-1111-1111-1111-111111111111", 0)
    ]
