"""Accounting and observation tests; never send provider requests."""

from collections import Counter
from dataclasses import asdict
from typing import Any

import httpx
import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from openai import APIConnectionError

from app.modules.rag.llm import TransientFallbackChatModel
from scripts.benchmark_evidence_selection import (
    EvidenceSelectionBenchmark,
    calculate_selection_metrics,
    load_cases,
)
from scripts.compare_evidence_selection_models import (
    CallTrace,
    ObservedChatModel,
    build_summaries,
    execution_schedule,
    is_comparable,
    summarize_calls,
)


def call_record(
    *, selected_ids: list[str], gold_ids: list[str], **overrides: Any
) -> dict[str, Any]:
    record = {
        "case_id": "example",
        "category": "generalist",
        "repetition": 1,
        "requested_model": "sabiazinho-4",
        "observed_model": "sabiazinho-4",
        "gold_ids": gold_ids,
        "selected_ids": selected_ids,
        "metrics": asdict(
            calculate_selection_metrics(selected_ids=selected_ids, gold_ids=gold_ids)
        ),
        "technical_failure": None,
        "fallback_used": False,
        "duration_ms": 2,
        "input_tokens": 10,
        "output_tokens": 5,
        "limitation": None,
    }
    record.update(overrides)
    return record


def test_schedule_balances_models_and_preserves_frozen_cases() -> None:
    cases = load_cases()
    before = [case.model_dump() for case in cases]
    schedule = execution_schedule(cases)
    assert len(schedule) == 72
    assert set(Counter((case.id, model) for _, case, model in schedule).values()) == {3}
    for offset in range(0, len(schedule), 2):
        first, second = schedule[offset : offset + 2]
        assert first[:2] == second[:2]
        assert first[2] != second[2]
    assert schedule[0][2] != schedule[2][2]
    assert schedule[0][2] != schedule[24][2]
    assert [case.model_dump() for case in cases] == before


@pytest.mark.anyio
async def test_observer_preserves_selection_and_captures_usage_and_limitation() -> None:
    message = AIMessage(
        content='{"unit_ids":["E1"],"limitation":"scope"}',
        response_metadata={"model_name": "sabiazinho-4"},
        usage_metadata={"input_tokens": 30, "output_tokens": 9, "total_tokens": 39},
    )
    trace = CallTrace()
    model = ObservedChatModel(
        delegate=FakeMessagesListChatModel(responses=[message]),
        trace=trace,
        role="primary",
    )
    result = await EvidenceSelectionBenchmark(llm=model).evaluate_case(load_cases()[0])
    assert result.selected_ids == ["E1"]
    assert result.observed_model == "sabiazinho-4"
    assert trace.has_decoded_limitation is True
    assert trace.limitation == "scope"
    assert (trace.input_tokens, trace.output_tokens) == (30, 9)
    assert trace.attempts == [
        {"role": "primary", "status": "success", "observed_model": "sabiazinho-4"}
    ]
    assert not hasattr(trace, "content")


class ConnectionFailureModel(FakeMessagesListChatModel):
    async def _agenerate(
        self, messages: list[BaseMessage], **kwargs: Any
    ) -> ChatResult:
        raise APIConnectionError(
            message="PRIVATE_PROVIDER_MESSAGE",
            request=httpx.Request("POST", "https://example.invalid"),
        )


@pytest.mark.anyio
async def test_fallback_is_observed_even_when_the_outer_call_succeeds() -> None:
    trace = CallTrace()
    primary = ConnectionFailureModel(responses=[])
    fallback = FakeMessagesListChatModel(
        responses=[
            AIMessage(
                content='{"unit_ids":[],"limitation":null}',
                response_metadata={"model_name": "fallback-model"},
            )
        ]
    )
    model = TransientFallbackChatModel(
        primary=ObservedChatModel(delegate=primary, trace=trace, role="primary"),
        fallback=ObservedChatModel(delegate=fallback, trace=trace, role="fallback"),
    )
    result = await EvidenceSelectionBenchmark(llm=model).evaluate_case(load_cases()[2])
    assert result.selected_ids == []
    assert result.observed_model == "fallback-model"
    assert [attempt["role"] for attempt in trace.attempts] == ["primary", "fallback"]
    assert trace.attempts[0]["error_type"] == "APIConnectionError"
    assert "PRIVATE_PROVIDER_MESSAGE" not in str(trace.attempts)


def test_fallback_unknown_model_and_failures_are_not_attributed_to_requested_model() -> (
    None
):
    records = [
        call_record(selected_ids=[], gold_ids=[]),
        call_record(
            selected_ids=["E1"],
            gold_ids=[],
            fallback_used=True,
            observed_model="fallback-model",
        ),
        call_record(selected_ids=["E1"], gold_ids=[], observed_model=None),
        call_record(
            selected_ids=[],
            gold_ids=[],
            technical_failure={"reason": "timeout"},
            metrics=None,
        ),
    ]
    assert [is_comparable(call) for call in records] == [True, False, False, False]
    summary = summarize_calls(records)
    assert summary["scheduled_calls"] == 4
    assert summary["comparable_calls"] == 1
    assert (
        summary["fallback_calls"]
        == summary["identity_excluded_calls"]
        == summary["technical_failure_count"]
        == 1
    )
    assert summary["semantic_metrics_comparable_only"]["negative_case_error_count"] == 0
    assert summary["technical_failure_rate"] == 0.25


def test_positive_coverage_is_distinct_from_merely_not_abstaining() -> None:
    summary = summarize_calls(
        [
            call_record(selected_ids=["E2"], gold_ids=["E1"]),
            call_record(selected_ids=["E1"], gold_ids=["E1"]),
        ]
    )
    assert summary["positive_coverage_rate"] == 0.5
    assert summary["semantic_metrics_comparable_only"]["false_abstention_count"] == 0


def test_thinking_comparison_keeps_paired_schedule_and_separate_summaries() -> None:
    cases = load_cases()
    models = ("sabia-4", "sabia-4-thinking")
    schedule = execution_schedule(cases, models)
    assert len(schedule) == 72
    assert {model for _, _, model in schedule} == set(models)
    assert set(Counter((case.id, model) for _, case, model in schedule).values()) == {3}
    assert schedule[0][2] != schedule[2][2]
    assert schedule[0][2] != schedule[24][2]
    calls = [
        call_record(
            case_id=case.id,
            repetition=repetition,
            requested_model=model,
            observed_model=model,
            selected_ids=case.gold_ids if model == "sabia-4" else [],
            gold_ids=case.gold_ids,
        )
        for repetition, case, model in schedule
    ]
    summaries = build_summaries(cases, calls, models)
    assert set(summaries) == set(models)
    assert summaries["sabia-4"]["all_calls"]["positive_coverage_rate"] == 1
    assert summaries["sabia-4-thinking"]["all_calls"]["positive_coverage_rate"] == 0


def test_repetition_summaries_measure_selection_sets_without_counting_new_cases() -> (
    None
):
    cases = load_cases()[:1]
    case = cases[0]
    calls = [
        call_record(
            case_id=case.id,
            repetition=repetition,
            selected_ids=ids,
            gold_ids=case.gold_ids,
        )
        for repetition, ids in [(1, ["E1"]), (2, ["E2", "E1"]), (3, ["E1", "E2"])]
    ]
    summary = build_summaries(cases, calls)["sabiazinho-4"]
    by_case = summary["by_case"][0]
    assert by_case["id_frequency"] == {"E1": 3, "E2": 2, "E3": 0}
    assert by_case["distinct_selected_sets"] == 2
    assert by_case["identical_across_all_three"] is False
    assert (
        summary["by_repetition"]["1"]["semantic_metrics_comparable_only"][
            "recall_micro"
        ]
        == 0.5
    )
    assert summary["mean_and_range_by_repetition"]["recall_micro"][
        "mean"
    ] == pytest.approx(5 / 6)
