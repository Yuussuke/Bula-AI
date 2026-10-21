from unittest.mock import Mock

import pytest
from langchain_core.runnables import RunnableLambda

from app.modules.rag import response_diagnostics
from app.modules.rag.grounded_generation import GroundedGenerationError
from app.modules.rag.response_diagnostics import ResponseStageObserver


@pytest.mark.parametrize(
    "stage", ["retrieval", "evidence_selection", "answer_validation"]
)
def test_stage_failure_is_logged_without_payload_and_propagated(
    stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = RuntimeError("private question or provider body")
    captured_logger = Mock()
    monkeypatch.setattr(response_diagnostics, "logger", captured_logger)

    def fail(inputs: dict[str, object]) -> str:
        raise failure

    observed = ResponseStageObserver().wrap(stage=stage, runnable=RunnableLambda(fail))
    with pytest.raises(RuntimeError) as raised:
        observed.invoke({"diagnostic_id": "test-run", "question": "private question"})
    assert raised.value is failure
    captured_logger.info.assert_called_once()
    assert captured_logger.info.call_args.args == ("rag_response_stage",)
    logged_fields = captured_logger.info.call_args.kwargs
    assert logged_fields["stage"] == stage
    assert logged_fields["status"] == "error"
    assert logged_fields["failure_reason"] == "internal_error"
    assert logged_fields["diagnostic_id"] == "test-run"
    assert "private question" not in str(logged_fields)


def test_sync_observation_preserves_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_logger = Mock()
    monkeypatch.setattr(response_diagnostics, "logger", captured_logger)

    def answer(inputs: dict[str, object]) -> dict[str, object]:
        return {"answer": "unchanged", "source_chunks": []}

    observed = ResponseStageObserver().wrap(
        stage="answer_validation", runnable=RunnableLambda(answer)
    )
    result = observed.invoke({"diagnostic_id": "test-run"})
    assert result == {"answer": "unchanged", "source_chunks": []}
    captured_logger.info.assert_called_once()
    logged_fields = captured_logger.info.call_args.kwargs
    assert logged_fields["status"] == "success"
    assert logged_fields["failure_reason"] is None


@pytest.mark.parametrize(
    "reason",
    ["missing_source_citation", "unknown_source_citation", "malformed_source_citation"],
)
def test_generation_contract_failure_keeps_reason_without_logging_content(
    reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_logger = Mock()
    monkeypatch.setattr(response_diagnostics, "logger", captured_logger)
    failure = GroundedGenerationError(reason)

    def fail(inputs: dict[str, object]) -> str:
        raise failure

    observed = ResponseStageObserver().wrap(
        stage="generation", runnable=RunnableLambda(fail)
    )
    with pytest.raises(GroundedGenerationError) as raised:
        observed.invoke({"diagnostic_id": "test-run", "question": "private question"})

    assert raised.value is failure
    logged_fields = captured_logger.info.call_args.kwargs
    assert logged_fields["stage"] == "generation"
    assert logged_fields["failure_reason"] == reason
    assert "private question" not in str(logged_fields)
