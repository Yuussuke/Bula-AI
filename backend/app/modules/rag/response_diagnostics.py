"""Payload-free instrumentation; does not change runnable results or exceptions."""

from time import perf_counter
from typing import TypeVar

import structlog
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from openai import APIConnectionError, APIError, APITimeoutError

logger = structlog.get_logger(__name__)
StageOutput = TypeVar("StageOutput")


class ResponseStageObserver:
    def wrap(
        self,
        *,
        stage: str,
        runnable: Runnable[dict[str, object], StageOutput],
    ) -> Runnable[dict[str, object], StageOutput]:
        def invoke(inputs: dict[str, object], config: RunnableConfig) -> StageOutput:
            started_at = perf_counter()
            try:
                result = runnable.invoke(inputs, config=config)
            except Exception as error:
                self.record(
                    stage=stage, inputs=inputs, started_at=started_at, error=error
                )
                raise
            self.record(stage=stage, inputs=inputs, started_at=started_at)
            return result

        async def ainvoke(
            inputs: dict[str, object], config: RunnableConfig
        ) -> StageOutput:
            started_at = perf_counter()
            try:
                result = await runnable.ainvoke(inputs, config=config)
            except Exception as error:
                self.record(
                    stage=stage, inputs=inputs, started_at=started_at, error=error
                )
                raise
            self.record(stage=stage, inputs=inputs, started_at=started_at)
            return result

        return RunnableLambda(invoke, afunc=ainvoke)

    def record(
        self,
        *,
        stage: str,
        inputs: dict[str, object],
        started_at: float,
        error: Exception | None = None,
    ) -> None:
        # Never log exception messages: providers may include request bodies.
        logger.info(
            "rag_response_stage",
            diagnostic_id=inputs.get("diagnostic_id"),
            stage=stage,
            status="error" if error is not None else "success",
            duration_ms=round((perf_counter() - started_at) * 1000, 3),
            failure_reason=self.classify_error(error) if error is not None else None,
        )

    def classify_error(self, error: Exception) -> str:
        if isinstance(error, (TimeoutError, APITimeoutError)):
            return "timeout"
        if isinstance(error, APIConnectionError):
            return "provider_connection_error"
        if isinstance(error, APIError):
            return "provider_api_error"
        return "internal_error"
