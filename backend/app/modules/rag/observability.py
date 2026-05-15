from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import time
from typing import Any, Literal

import structlog


RAG_INGESTION_LOG_SCHEMA_VERSION = 1

IngestionStatus = Literal["succeeded", "failed"]
StageStatus = Literal["succeeded", "failed"]

logger = structlog.get_logger(__name__)


@dataclass
class RAGIngestionStageContext:
    fields: dict[str, object] = field(default_factory=dict)

    def add_fields(self, **fields: object) -> None:
        self.fields.update(fields)


class RAGIngestionObserver:
    """
    Structured timing helper for one RAG ingestion run.

    This uses time.perf_counter() only to measure elapsed time inside one local
    execution. The raw clock value is not a timestamp and should not be compared
    across processes, workers, machines, or independent execution contexts.
    """

    def __init__(
        self,
        *,
        run_id: str,
        bula_id: str,
        doc_id: str,
        log: Any = logger,
    ) -> None:
        self.run_id = run_id
        self.bula_id = bula_id
        self.doc_id = doc_id
        self._logger = log
        self._run_started_at = time.perf_counter()
        self._stage_durations_ms: dict[str, float] = {}

    def start(self) -> None:
        self._logger.info(
            "rag_ingestion_started",
            **self._common_fields(),
        )

    @asynccontextmanager
    async def stage(self, stage: str) -> AsyncIterator[RAGIngestionStageContext]:
        stage_context = RAGIngestionStageContext()
        stage_started_at = time.perf_counter()

        self._logger.debug(
            "rag_ingestion_stage_started",
            **self._common_fields(),
            stage=stage,
        )

        try:
            yield stage_context
        except BaseException as exc:
            self._finish_stage(
                stage=stage,
                stage_started_at=stage_started_at,
                stage_status="failed",
                fields=stage_context.fields,
                error=exc,
            )
            raise

        self._finish_stage(
            stage=stage,
            stage_started_at=stage_started_at,
            stage_status="succeeded",
            fields=stage_context.fields,
            error=None,
        )

    def finish(self, *, error: BaseException | None = None) -> None:
        ingestion_status: IngestionStatus = (
            "failed" if error is not None else "succeeded"
        )
        slowest_stage, slowest_stage_duration_ms = self._find_slowest_stage()

        log_fields: dict[str, object] = {
            **self._common_fields(),
            "ingestion_status": ingestion_status,
            "total_duration_ms": self._elapsed_ms(self._run_started_at),
            "stage_durations_ms": dict(self._stage_durations_ms),
            "slowest_stage": slowest_stage,
            "slowest_stage_duration_ms": slowest_stage_duration_ms,
        }
        if error is not None:
            log_fields["error_type"] = error.__class__.__name__

        self._logger.info("rag_ingestion_finished", **log_fields)

    def _finish_stage(
        self,
        *,
        stage: str,
        stage_started_at: float,
        stage_status: StageStatus,
        fields: dict[str, object],
        error: BaseException | None,
    ) -> None:
        duration_ms = self._elapsed_ms(stage_started_at)
        self._stage_durations_ms[stage] = duration_ms

        log_fields: dict[str, object] = {
            **self._common_fields(),
            **fields,
            "stage": stage,
            "stage_status": stage_status,
            "duration_ms": duration_ms,
        }
        if error is not None:
            log_fields["error_type"] = error.__class__.__name__

        self._logger.info("rag_ingestion_stage_finished", **log_fields)

    def _find_slowest_stage(self) -> tuple[str | None, float | None]:
        if not self._stage_durations_ms:
            return None, None

        slowest_stage, duration_ms = max(
            self._stage_durations_ms.items(),
            key=lambda item: item[1],
        )
        return slowest_stage, duration_ms

    def _common_fields(self) -> dict[str, object]:
        return {
            "log_schema_version": RAG_INGESTION_LOG_SCHEMA_VERSION,
            "run_id": self.run_id,
            "bula_id": self.bula_id,
            "doc_id": self.doc_id,
        }

    def _elapsed_ms(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 2)
