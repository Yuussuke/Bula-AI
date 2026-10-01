"""Benchmark accounting and isolation; these do not measure live model quality."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.rag import llm as rag_llm
from scripts import benchmark_evidence_selection

from scripts.benchmark_evidence_selection import (
    CaseResult,
    EvidenceSelectionBenchmark,
    EvidenceSelectionCase,
    FrozenEvidenceUnit,
    aggregate_results,
    build_selector_messages,
    calculate_selection_metrics,
    load_cases,
)


def example_case(*, gold_ids: list[str] | None = None) -> EvidenceSelectionCase:
    return EvidenceSelectionCase(
        id="example",
        category="generalist",
        source_origin="PRIVATE_ORIGIN_TOKEN",
        question="Qual informação o documento traz?",
        units=[
            FrozenEvidenceUnit(
                id="E1",
                source=1,
                section="Uso",
                kind="prose",
                text="Primeira informação.",
            ),
            FrozenEvidenceUnit(
                id="E2",
                source=2,
                section="Uso",
                kind="prose",
                text="Segunda informação.",
            ),
            FrozenEvidenceUnit(
                id="E3",
                source=3,
                section="Conservação",
                kind="prose",
                text="Informação tangencial.",
            ),
        ],
        gold_ids=["E1", "E2"] if gold_ids is None else gold_ids,
        annotation_notes="PRIVATE_ANNOTATION_TOKEN",
    )


def valid_result(
    *, case_id: str, selected_ids: list[str], gold_ids: list[str]
) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        category="generalist",
        gold_ids=gold_ids,
        selected_ids=selected_ids,
        metrics=calculate_selection_metrics(
            selected_ids=selected_ids, gold_ids=gold_ids
        ),
        technical_failure=None,
        duration_ms=1,
    )


def test_partial_selection_reports_missing_and_tangential_ids() -> None:
    metrics = calculate_selection_metrics(
        selected_ids=["E1", "E3"], gold_ids=["E1", "E2"]
    )

    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.exact_set_match is False
    assert metrics.tangential_ids == ["E3"]
    assert metrics.tangential_rate == 0.5
    assert metrics.missing_gold_ids == ["E2"]
    assert metrics.false_abstention is False


def test_second_relevant_unit_is_not_penalized_and_ids_are_scored_as_sets() -> None:
    metrics = calculate_selection_metrics(
        selected_ids=["E2", "E1", "E2"], gold_ids=["E1", "E2"]
    )

    assert metrics.precision == metrics.recall == 1
    assert metrics.exact_set_match is True
    assert metrics.selected_count == 2
    assert metrics.tangential_count == 0


def test_empty_selection_is_not_awarded_perfect_precision() -> None:
    metrics = calculate_selection_metrics(selected_ids=[], gold_ids=["E1"])

    assert metrics.precision is None
    assert metrics.recall == 0
    assert metrics.false_abstention is True
    assert metrics.exact_set_match is False
    assert metrics.negative_case_error is None


def test_correct_negative_case_has_undefined_precision_and_recall() -> None:
    metrics = calculate_selection_metrics(selected_ids=[], gold_ids=[])

    assert metrics.precision is None
    assert metrics.recall is None
    assert metrics.exact_set_match is True
    assert metrics.negative_case_error is False
    assert metrics.false_abstention is False


def test_selection_in_negative_case_is_tangential_not_false_abstention() -> None:
    metrics = calculate_selection_metrics(selected_ids=["E1"], gold_ids=[])

    assert metrics.precision == 0
    assert metrics.recall is None
    assert metrics.tangential_rate == 1
    assert metrics.negative_case_error is True
    assert metrics.false_abstention is False


def test_aggregation_keeps_metric_denominators_and_technical_errors_separate() -> None:
    results = [
        valid_result(case_id="mixed", selected_ids=["E1", "E3"], gold_ids=["E1", "E2"]),
        valid_result(case_id="abstention", selected_ids=[], gold_ids=["E1"]),
        valid_result(case_id="correct_negative", selected_ids=[], gold_ids=[]),
        valid_result(case_id="wrong_negative", selected_ids=["E1"], gold_ids=[]),
        CaseResult(
            case_id="technical",
            category="generalist",
            gold_ids=["E1"],
            selected_ids=None,
            metrics=None,
            technical_failure={"reason": "timeout"},
            duration_ms=1,
        ),
    ]

    report = aggregate_results(results)

    assert report["attempted_cases"] == 5
    assert report["valid_cases"] == 4
    assert report["precision_micro"] == report["recall_micro"] == pytest.approx(1 / 3)
    assert report["precision_macro"] == report["recall_macro"] == 0.25
    assert report["precision_defined_cases"] == report["recall_defined_cases"] == 2
    assert report["exact_set_match_rate"] == 0.25
    assert report["tangential_evidence_count"] == 2
    assert report["tangential_evidence_rate"] == pytest.approx(2 / 3)
    assert report["case_tangential_rate"] == 0.5
    assert report["false_abstention_rate"] == 0.5
    assert report["negative_case_error_rate"] == 0.5
    assert report["technical_failure_rate"] == 0.2


def test_all_technical_failures_do_not_become_documentary_abstentions() -> None:
    result = CaseResult(
        case_id="failed",
        category="generalist",
        gold_ids=[],
        selected_ids=None,
        metrics=None,
        technical_failure={"reason": "invalid_json"},
        duration_ms=1,
    )
    report = aggregate_results([result])

    assert report["technical_failure_count"] == 1
    assert report["valid_cases"] == 0
    assert report["exact_set_match_rate"] is None
    assert report["false_abstention_rate"] is None
    assert report["negative_case_error_rate"] is None


def test_messages_include_frozen_units_but_never_annotations_or_gold() -> None:
    case = example_case()
    original_messages = build_selector_messages(case)
    changed_gold_case = case.model_copy(
        update={"gold_ids": [], "annotation_notes": "DIFFERENT_PRIVATE_TOKEN"}
    )

    assert build_selector_messages(changed_gold_case) == original_messages
    message_text = "\n".join(str(message.content) for message in original_messages)
    assert "PRIVATE_ANNOTATION_TOKEN" not in message_text
    assert "PRIVATE_ORIGIN_TOKEN" not in message_text
    assert "gold_ids" not in message_text
    assert (
        "[E3] Fonte 3; seção: Conservação; tipo: prose\nInformação tangencial."
        in message_text
    )


def test_fixtures_are_small_frozen_sets_and_exclude_retrieval_gap() -> None:
    cases = load_cases()

    assert len(cases) == 12
    assert sum(case.category == "regression" for case in cases) == 4
    assert sum(case.category == "generalist" for case in cases) == 8
    assert all(len(case.units) > 1 for case in cases)
    assert all(len(case.gold_ids) <= 6 for case in cases)
    assert all("dor de cabeça" not in case.question for case in cases)
    age_case = next(
        case for case in cases if case.id == "regression_age_with_renal_table"
    )
    renal_row = next(unit for unit in age_case.units if unit.id == "E12")
    assert renal_row.text.startswith(
        "## Posologia para insuficiência renal (dos rins)\nAdultos\n"
    )
    assert age_case.gold_ids == ["E2", "E6"]
    assert sum(not case.gold_ids for case in cases) == 3


def test_loader_rejects_orphan_gold_and_duplicate_scenario_ids(tmp_path: Path) -> None:
    case = example_case().model_dump(mode="json")
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([{**case, "gold_ids": ["E99"]}]), encoding="utf-8")
    with pytest.raises(ValidationError, match="Every gold ID"):
        load_cases(path)
    path.write_text(json.dumps([case, case]), encoding="utf-8")
    with pytest.raises(ValueError, match="Scenario IDs must be unique"):
        load_cases(path)


@pytest.mark.anyio
async def test_selector_ids_are_scored_without_clinical_postprocessing() -> None:
    llm = FakeMessagesListChatModel(
        responses=[
            AIMessage(content='{"unit_ids":["E1","E3"],"limitation":"individual"}')
        ]
    )
    result = await EvidenceSelectionBenchmark(llm=llm).evaluate_case(example_case())

    assert result.selected_ids == ["E1", "E3"]
    assert result.metrics is not None
    assert result.metrics.precision == 0.5
    assert result.metrics.tangential_ids == ["E3"]
    assert result.technical_failure is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content, reason",
    [
        ("malformed PRIVATE_BODY_TOKEN", "invalid_json"),
        ('{"unit_ids":["E1"]}', "invalid_schema"),
        (
            '{"unit_ids":["PRIVATE_UNKNOWN_TOKEN"],"limitation":null}',
            "unknown_evidence_id",
        ),
    ],
)
async def test_contract_errors_are_not_scored_as_empty_evidence(
    content: str, reason: str
) -> None:
    llm = FakeMessagesListChatModel(responses=[AIMessage(content=content)])
    result = await EvidenceSelectionBenchmark(llm=llm).evaluate_case(example_case())

    assert result.metrics is None
    assert result.selected_ids is None
    assert result.technical_failure is not None
    assert result.technical_failure["reason"] == reason
    assert "PRIVATE_" not in json.dumps(asdict(result))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error, reason",
    [
        (TimeoutError("PRIVATE_TIMEOUT_TOKEN"), "timeout"),
        (RuntimeError("PRIVATE_API_TOKEN"), "provider_error"),
    ],
)
async def test_provider_failures_do_not_become_false_abstentions(
    error: Exception, reason: str
) -> None:
    llm = Mock(spec=BaseChatModel)
    llm.bind.return_value.ainvoke = AsyncMock(side_effect=error)
    result = await EvidenceSelectionBenchmark(llm=llm).evaluate_case(example_case())

    assert result.metrics is None
    assert result.technical_failure is not None
    assert result.technical_failure["reason"] == reason
    assert "PRIVATE_" not in json.dumps(asdict(result))


@pytest.mark.anyio
async def test_all_cases_are_evaluated_even_after_a_contract_failure() -> None:
    llm = FakeMessagesListChatModel(
        responses=[
            AIMessage(content="invalid JSON"),
            AIMessage(content='{"unit_ids":[],"limitation":"missing"}'),
        ]
    )
    results = await EvidenceSelectionBenchmark(llm=llm).evaluate_cases(
        [example_case(), example_case(gold_ids=[])]
    )

    assert len(results) == 2
    assert results[0].metrics is None
    assert results[1].metrics is not None
    assert results[1].metrics.exact_set_match is True
    assert aggregate_results(results)["technical_failure_count"] == 1


def test_cli_requires_explicit_opt_in_before_provider_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_provider(*, settings: Settings) -> BaseChatModel:
        raise AssertionError("A provider must not be constructed without opt-in.")

    monkeypatch.setattr(sys, "argv", ["benchmark_evidence_selection"])
    monkeypatch.setattr(rag_llm, "get_llm", forbidden_provider)

    with pytest.raises(SystemExit) as error:
        benchmark_evidence_selection.main()

    assert error.value.code == 2


@pytest.mark.anyio
async def test_report_has_per_case_and_aggregate_metrics_not_raw_model_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = load_cases()
    model = FakeMessagesListChatModel(
        responses=[
            AIMessage(
                content=json.dumps({"unit_ids": case.gold_ids, "limitation": None}),
                response_metadata={"model_name": "offline-stub"},
            )
            for case in cases
        ]
    )

    def build_test_model(*, settings: Settings) -> BaseChatModel:
        return model

    monkeypatch.setattr(rag_llm, "get_llm", build_test_model)
    report = await benchmark_evidence_selection.run_benchmark()
    aggregate = report["aggregate"]

    assert isinstance(aggregate, dict)
    assert aggregate["exact_set_match_count"] == aggregate["attempted_cases"] == 12
    assert aggregate["precision_micro"] == aggregate["recall_micro"] == 1
    assert aggregate["technical_failure_count"] == 0
    assert len(report["fixtures_sha256"]) == len(report["prompt_sha256"]) == 64
    case_reports = report["cases"]
    assert isinstance(case_reports, list)
    assert len(case_reports) == 12
    assert all(case["observed_model"] == "offline-stub" for case in case_reports)
    serialized = json.dumps(report)
    assert "unit_ids" not in serialized
    assert cases[0].units[0].text not in serialized
    assert cases[0].annotation_notes not in serialized
