"""Auxiliary development benchmark; never part of the application RAG flow."""

import argparse
import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.modules.rag.chain import EVIDENCE_SELECTION_PROMPT
from app.modules.rag.context_assessment import (
    ContextAssessment,
    EvidenceAssessmentDecoder,
)
from app.modules.rag.evidence_units import (
    EvidenceUnit,
    EvidenceUnitKind,
    format_evidence_units,
)


DEFAULT_FIXTURES = (
    Path(__file__).parents[1] / "tests/fixtures/rag/evidence_selection_cases.json"
)


class FrozenEvidenceUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: int = Field(ge=1)
    section: str
    kind: EvidenceUnitKind
    text: str

    def to_evidence_unit(self) -> EvidenceUnit:
        # Source container for the formatter only: no extraction or DB query.
        return EvidenceUnit(
            unit_id=self.id,
            source_number=self.source,
            section_title=self.section,
            kind=self.kind,
            text=self.text,
            document=Document(page_content=self.text),
        )


class EvidenceSelectionCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: Literal["regression", "generalist"]
    source_origin: str
    question: str
    units: list[FrozenEvidenceUnit] = Field(min_length=1)
    gold_ids: list[str]
    annotation_notes: str

    @model_validator(mode="after")
    def validate_annotations(self) -> "EvidenceSelectionCase":
        unit_ids = [unit.id for unit in self.units]
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("Candidate IDs must be unique within a case.")
        if len(set(self.gold_ids)) != len(self.gold_ids):
            raise ValueError("Gold IDs must be unique within a case.")
        if not set(self.gold_ids).issubset(unit_ids):
            raise ValueError("Every gold ID must refer to a supplied candidate.")
        return self


def load_cases(path: Path = DEFAULT_FIXTURES) -> list[EvidenceSelectionCase]:
    cases = [
        EvidenceSelectionCase.model_validate(case)
        for case in json.loads(path.read_text(encoding="utf-8"))
    ]
    if not cases:
        raise ValueError("At least one base scenario is required.")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Scenario IDs must be unique; variants are not base cases.")
    return cases


def build_selector_messages(case: EvidenceSelectionCase) -> list[BaseMessage]:
    units = [unit.to_evidence_unit() for unit in case.units]
    return EVIDENCE_SELECTION_PROMPT.invoke(
        {
            "question": case.question,
            "context": format_evidence_units(units),
            "chat_history": [],
        }
    ).to_messages()


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


@dataclass(frozen=True)
class SelectionMetrics:
    selected_count: int
    gold_count: int
    true_positive_count: int
    precision: float | None
    recall: float | None
    exact_set_match: bool
    tangential_ids: list[str]
    tangential_count: int
    tangential_rate: float | None
    missing_gold_ids: list[str]
    false_abstention: bool
    negative_case_error: bool | None


def calculate_selection_metrics(
    *, selected_ids: list[str], gold_ids: list[str]
) -> SelectionMetrics:
    selected = set(selected_ids)
    gold = set(gold_ids)
    true_positive_count = len(selected & gold)
    tangential_ids = sorted(selected - gold)
    return SelectionMetrics(
        selected_count=len(selected),
        gold_count=len(gold),
        true_positive_count=true_positive_count,
        precision=_ratio(true_positive_count, len(selected)),
        recall=_ratio(true_positive_count, len(gold)),
        exact_set_match=selected == gold,
        tangential_ids=tangential_ids,
        tangential_count=len(tangential_ids),
        tangential_rate=_ratio(len(tangential_ids), len(selected)),
        missing_gold_ids=sorted(gold - selected),
        false_abstention=bool(gold) and not selected,
        negative_case_error=bool(selected) if not gold else None,
    )


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    gold_ids: list[str]
    selected_ids: list[str] | None
    metrics: SelectionMetrics | None
    technical_failure: dict[str, object] | None
    duration_ms: float
    observed_model: str | None = None


def aggregate_results(results: list[CaseResult]) -> dict[str, object]:
    metrics = [result.metrics for result in results if result.metrics is not None]
    total_selected = sum(metric.selected_count for metric in metrics)
    total_gold = sum(metric.gold_count for metric in metrics)
    total_correct = sum(metric.true_positive_count for metric in metrics)
    total_tangential = sum(metric.tangential_count for metric in metrics)
    positive_count = sum(metric.gold_count > 0 for metric in metrics)
    negative_count = sum(metric.gold_count == 0 for metric in metrics)
    precision_values = [
        metric.precision for metric in metrics if metric.precision is not None
    ]
    recall_values = [metric.recall for metric in metrics if metric.recall is not None]
    exact_count = sum(metric.exact_set_match for metric in metrics)
    tangential_case_count = sum(metric.tangential_count > 0 for metric in metrics)
    abstention_count = sum(metric.false_abstention for metric in metrics)
    negative_error_count = sum(metric.negative_case_error is True for metric in metrics)
    return {
        "attempted_cases": len(results),
        "valid_cases": len(metrics),
        "valid_positive_cases": positive_count,
        "valid_negative_cases": negative_count,
        "precision_micro": _ratio(total_correct, total_selected),
        "recall_micro": _ratio(total_correct, total_gold),
        "precision_macro": sum(precision_values) / len(precision_values)
        if precision_values
        else None,
        "recall_macro": sum(recall_values) / len(recall_values)
        if recall_values
        else None,
        "precision_defined_cases": len(precision_values),
        "recall_defined_cases": len(recall_values),
        "exact_set_match_count": exact_count,
        "exact_set_match_rate": _ratio(exact_count, len(metrics)),
        "selected_evidence_count": total_selected,
        "tangential_evidence_count": total_tangential,
        "tangential_evidence_rate": _ratio(total_tangential, total_selected),
        "cases_with_tangential_evidence": tangential_case_count,
        "case_tangential_rate": _ratio(tangential_case_count, len(metrics)),
        "false_abstention_count": abstention_count,
        "false_abstention_rate": _ratio(abstention_count, positive_count),
        "negative_case_error_count": negative_error_count,
        "negative_case_error_rate": _ratio(negative_error_count, negative_count),
        "technical_failure_count": len(results) - len(metrics),
        "technical_failure_rate": _ratio(len(results) - len(metrics), len(results)),
    }


class EvidenceSelectionBenchmark:
    def __init__(self, *, llm: BaseChatModel, timeout_seconds: float = 30) -> None:
        self.selector = llm.bind(
            response_format=ContextAssessment.provider_response_format()
        )
        self.timeout_seconds = timeout_seconds

    async def evaluate_case(self, case: EvidenceSelectionCase) -> CaseResult:
        started_at = time.perf_counter()
        selected_ids: list[str] | None = None
        observed_model: str | None = None
        failure: dict[str, object] | None = None
        metrics: SelectionMetrics | None = None
        try:
            response = await asyncio.wait_for(
                self.selector.ainvoke(build_selector_messages(case)),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as error:
            failure = {
                "stage": "provider",
                "reason": "timeout",
                "error_type": type(error).__name__,
            }
        except Exception as error:
            # Provider exception prose can contain secrets; never serialize it.
            failure = {
                "stage": "provider",
                "reason": "provider_error",
                "error_type": type(error).__name__,
            }
        else:
            model_name = response.response_metadata.get("model_name")
            observed_model = model_name if isinstance(model_name, str) else None
            try:
                selection = EvidenceAssessmentDecoder().decode(
                    StrOutputParser().invoke(response)
                )
            except json.JSONDecodeError as error:
                failure = {
                    "stage": "contract",
                    "reason": "invalid_json",
                    "error_type": type(error).__name__,
                    "line": error.lineno,
                    "column": error.colno,
                }
            except ValidationError as error:
                failure = {
                    "stage": "contract",
                    "reason": "invalid_schema",
                    "error_type": type(error).__name__,
                    "issue_types": [
                        issue["type"] for issue in error.errors(include_input=False)
                    ],
                }
            except Exception as error:
                failure = {
                    "stage": "contract",
                    "reason": "invalid_response",
                    "error_type": type(error).__name__,
                }
            else:
                selected_ids = selection.unit_ids
                unknown_ids = sorted(
                    set(selected_ids) - {unit.id for unit in case.units}
                )
                if unknown_ids:
                    # Invalid provider IDs are not documental false positives.
                    failure = {
                        "stage": "contract",
                        "reason": "unknown_evidence_id",
                        "unknown_id_count": len(unknown_ids),
                    }
                    selected_ids = None
                else:
                    metrics = calculate_selection_metrics(
                        selected_ids=selected_ids, gold_ids=case.gold_ids
                    )
        return CaseResult(
            case_id=case.id,
            category=case.category,
            gold_ids=case.gold_ids,
            selected_ids=selected_ids,
            metrics=metrics,
            technical_failure=failure,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
            observed_model=observed_model,
        )

    async def evaluate_cases(
        self, cases: list[EvidenceSelectionCase]
    ) -> list[CaseResult]:
        results: list[CaseResult] = []
        for case in cases:
            results.append(await self.evaluate_case(case))
        return results


async def run_benchmark(*, fixtures: Path = DEFAULT_FIXTURES) -> dict[str, object]:
    # Offline accounting and CLI help do not need provider credentials/settings.
    from app.core.config import get_settings
    from app.modules.rag.llm import get_llm

    cases = load_cases(fixtures)
    fixtures_checksum = hashlib.sha256(fixtures.read_bytes()).hexdigest()
    settings = get_settings()
    benchmark = EvidenceSelectionBenchmark(llm=get_llm(settings=settings))
    results = await benchmark.evaluate_cases(cases)
    prompt_text = "\n".join(
        str(message.content)
        for message in EVIDENCE_SELECTION_PROMPT.invoke(
            {"question": "", "context": "", "chat_history": []}
        ).to_messages()
    )
    return {
        "purpose": "auxiliary_groundedness_development_check_not_main_TCC_evaluation",
        "created_at": datetime.now(UTC).isoformat(),
        "fixtures_sha256": fixtures_checksum,
        "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
        "configured_provider": settings.llm.provider,
        "configured_maritaca_model": settings.maritaca_model,
        "configured_openrouter_model": settings.openrouter.chat_model,
        "configured_fallback_enabled": settings.llm.enable_fallback,
        "aggregate": aggregate_results(results),
        "cases": [asdict(result) for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-provider-requests", action="store_true")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument(
        "--output", type=Path, default=Path("tmp/evidence-selection/results.json")
    )
    arguments = parser.parse_args()
    if not arguments.allow_provider_requests:
        parser.error(
            "Explicit --allow-provider-requests is required; API calls may cost credits."
        )
    report = asyncio.run(run_benchmark(fixtures=arguments.fixtures))
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(serialized_report + "\n", encoding="utf-8")
    print(serialized_report)


if __name__ == "__main__":
    main()
