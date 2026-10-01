"""Fixed, paired model comparison for the development-only selection benchmark."""

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import ChatResult
from pydantic import ConfigDict

from scripts.benchmark_evidence_selection import (
    DEFAULT_FIXTURES,
    CaseResult,
    EvidenceSelectionBenchmark,
    EvidenceSelectionCase,
    SelectionMetrics,
    aggregate_results,
    build_selector_messages,
    load_cases,
)
from app.modules.rag.chain import EVIDENCE_SELECTION_PROMPT
from app.modules.rag.context_assessment import (
    ContextAssessment,
    EvidenceAssessmentDecoder,
)


MODELS = ("sabiazinho-4", "sabia-4")
REPETITIONS = (1, 2, 3)


class CallTrace:
    """Allowlisted metadata only; no response bodies, request bodies or secrets."""

    def __init__(self) -> None:
        self.attempts: list[dict[str, object]] = []
        self.limitation: str | None = None
        self.has_decoded_limitation = False
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None

    def reset(self) -> None:
        self.__init__()

    def capture(self, result: ChatResult, attempt: dict[str, object]) -> None:
        output = result.llm_output or {}
        message = result.generations[0].message
        attempt["observed_model"] = output.get(
            "model_name"
        ) or message.response_metadata.get("model_name")
        usage = getattr(message, "usage_metadata", None) or {}
        legacy_usage = output.get("token_usage") or {}
        self.input_tokens = usage.get("input_tokens", legacy_usage.get("prompt_tokens"))
        self.output_tokens = usage.get(
            "output_tokens", legacy_usage.get("completion_tokens")
        )
        try:
            assessment = EvidenceAssessmentDecoder().decode(
                StrOutputParser().invoke(message)
            )
        except Exception:
            # The unchanged benchmark decoder records the original technical category.
            return
        self.has_decoded_limitation = True
        self.limitation = assessment.limitation.value if assessment.limitation else None


class ObservedChatModel(BaseChatModel):
    delegate: BaseChatModel
    trace: CallTrace
    role: str
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "evaluation-metadata-observer"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        raise NotImplementedError("This diagnostic runs async calls only.")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        attempt: dict[str, object] = {"role": self.role, "status": "started"}
        self.trace.attempts.append(attempt)
        try:
            result = await self.delegate._agenerate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
        except asyncio.CancelledError:
            attempt.update(status="cancelled", error_type="CancelledError")
            raise
        except Exception as error:
            attempt.update(status="error", error_type=type(error).__name__)
            raise
        attempt["status"] = "success"
        self.trace.capture(result, attempt)
        return result


def execution_schedule(
    cases: list[EvidenceSelectionCase],
    models: tuple[str, str] = MODELS,
) -> list[tuple[int, EvidenceSelectionCase, str]]:
    schedule = []
    for repetition in REPETITIONS:
        for case_index, case in enumerate(cases):
            ordered_models = (
                models
                if (case_index + repetition - 1) % 2 == 0
                else tuple(reversed(models))
            )
            schedule.extend((repetition, case, model) for model in ordered_models)
    return schedule


def is_comparable(call: dict[str, Any]) -> bool:
    return (
        call["technical_failure"] is None
        and not call["fallback_used"]
        and call["observed_model"] == call["requested_model"]
    )


def summarize_calls(calls: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [call for call in calls if is_comparable(call)]
    results = [
        CaseResult(
            case_id=call["case_id"],
            category=call["category"],
            gold_ids=call["gold_ids"],
            selected_ids=call["selected_ids"],
            metrics=SelectionMetrics(**call["metrics"]),
            technical_failure=None,
            duration_ms=call["duration_ms"],
            observed_model=call["observed_model"],
        )
        for call in eligible
    ]
    metrics = aggregate_results(results)
    positive_calls = [call for call in eligible if call["gold_ids"]]
    covered = sum(call["metrics"]["true_positive_count"] > 0 for call in positive_calls)
    return {
        "scheduled_calls": len(calls),
        "comparable_calls": len(eligible),
        "fallback_calls": sum(call["fallback_used"] for call in calls),
        "technical_failure_count": sum(
            call["technical_failure"] is not None for call in calls
        ),
        "technical_failure_rate": sum(
            call["technical_failure"] is not None for call in calls
        )
        / len(calls)
        if calls
        else None,
        "identity_excluded_calls": sum(
            call["technical_failure"] is None
            and not call["fallback_used"]
            and call["observed_model"] != call["requested_model"]
            for call in calls
        ),
        "semantic_metrics_comparable_only": metrics,
        "positive_calls_with_any_gold": covered,
        "positive_coverage_rate": covered / len(positive_calls)
        if positive_calls
        else None,
        "mean_latency_ms_all_calls": mean(call["duration_ms"] for call in calls)
        if calls
        else None,
        "input_tokens_reported": sum(
            call["input_tokens"] for call in calls if call["input_tokens"] is not None
        ),
        "output_tokens_reported": sum(
            call["output_tokens"] for call in calls if call["output_tokens"] is not None
        ),
        "calls_with_token_usage": sum(
            call["input_tokens"] is not None and call["output_tokens"] is not None
            for call in calls
        ),
    }


def summarize_case(
    case: EvidenceSelectionCase, calls: list[dict[str, Any]]
) -> dict[str, Any]:
    eligible = [call for call in calls if is_comparable(call)]
    selections = Counter(tuple(sorted(set(call["selected_ids"]))) for call in eligible)
    summary = summarize_calls(calls)
    summary.update(
        case_id=case.id,
        gold_ids=case.gold_ids,
        selections_by_repetition=[
            {
                "repetition": call["repetition"],
                "selected_ids": call["selected_ids"],
                "limitation": call["limitation"],
                "is_comparable": is_comparable(call),
                "technical_failure": call["technical_failure"],
            }
            for call in calls
        ],
        id_frequency={
            unit.id: sum(unit.id in call["selected_ids"] for call in eligible)
            for unit in case.units
        },
        empty_selection_count=sum(not call["selected_ids"] for call in eligible),
        empty_selection_rate=sum(not call["selected_ids"] for call in eligible)
        / len(eligible)
        if eligible
        else None,
        distinct_selected_sets=len(selections),
        identical_across_all_three=len(selections) == 1 if len(eligible) == 3 else None,
        selected_set_frequencies=[
            {"ids": list(ids), "count": count} for ids, count in selections.items()
        ],
        limitation_frequencies=dict(
            Counter(str(call["limitation"]) for call in eligible)
        ),
    )
    return summary


def build_summaries(
    cases: list[EvidenceSelectionCase],
    calls: list[dict[str, Any]],
    models: tuple[str, str] = MODELS,
) -> dict[str, Any]:
    summaries = {}
    for model in models:
        model_calls = [call for call in calls if call["requested_model"] == model]
        repetitions = {
            str(repetition): summarize_calls(
                [call for call in model_calls if call["repetition"] == repetition]
            )
            for repetition in REPETITIONS
        }
        metric_values: dict[str, list[float]] = {}
        for summary in repetitions.values():
            combined = {
                **summary["semantic_metrics_comparable_only"],
                **{
                    key: summary[key]
                    for key in (
                        "positive_coverage_rate",
                        "positive_calls_with_any_gold",
                        "technical_failure_count",
                        "technical_failure_rate",
                        "mean_latency_ms_all_calls",
                    )
                },
            }
            for key, value in combined.items():
                if isinstance(value, (int, float)):
                    metric_values.setdefault(key, []).append(value)
        summaries[model] = {
            "all_calls": summarize_calls(model_calls),
            "by_repetition": repetitions,
            "mean_and_range_by_repetition": {
                key: {
                    "mean": mean(values),
                    "min": min(values),
                    "max": max(values),
                    "defined_repetitions": len(values),
                }
                for key, values in metric_values.items()
            },
            "by_case": [
                summarize_case(
                    case, [call for call in model_calls if call["case_id"] == case.id]
                )
                for case in cases
            ],
        }
    return summaries


async def run_comparison(
    *,
    fixtures: Path,
    baseline: Path,
    output: Path,
    models: tuple[str, str] = MODELS,
) -> None:
    from app.core.config import get_settings
    from app.modules.rag.llm import TransientFallbackChatModel, get_llm

    if output.exists():
        raise ValueError(
            "Use a new output path; do not overwrite a completed or partial round."
        )
    if len(set(models)) != 2:
        raise ValueError("The comparison requires two distinct models.")
    baseline_report = json.loads(baseline.read_text(encoding="utf-8"))
    fixture_hash = hashlib.sha256(fixtures.read_bytes()).hexdigest()
    prompt_text = "\n".join(
        str(message.content)
        for message in EVIDENCE_SELECTION_PROMPT.invoke(
            {"question": "", "context": "", "chat_history": []}
        ).to_messages()
    )
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()
    if (
        fixture_hash != baseline_report["fixtures_sha256"]
        or prompt_hash != baseline_report["prompt_sha256"]
    ):
        raise ValueError("Frozen fixtures/prompt differ from the base benchmark.")
    cases = load_cases(fixtures)
    if len(cases) != 12:
        raise ValueError("Exactly the 12 frozen cases are required.")
    settings = get_settings()
    if settings.llm.provider != baseline_report["configured_provider"]:
        raise ValueError("Provider configuration differs from the base benchmark.")
    if (
        settings.llm.enable_fallback != baseline_report["configured_fallback_enabled"]
        or settings.openrouter.chat_model
        != baseline_report["configured_openrouter_model"]
    ):
        raise ValueError("Fallback configuration differs from the base benchmark.")
    benchmarks: dict[str, EvidenceSelectionBenchmark] = {}
    traces: dict[str, CallTrace] = {}
    for model in models:
        llm = get_llm(settings=settings.model_copy(update={"maritaca_model": model}))
        trace = CallTrace()
        if isinstance(llm, TransientFallbackChatModel):
            if llm.primary.temperature != 0.2 or llm.primary.model_name != model:
                raise ValueError("Unexpected primary model configuration.")
            llm = llm.model_copy(
                update={
                    "primary": ObservedChatModel(
                        delegate=llm.primary, trace=trace, role="primary"
                    ),
                    "fallback": ObservedChatModel(
                        delegate=llm.fallback, trace=trace, role="fallback"
                    ),
                }
            )
        else:
            if llm.temperature != 0.2 or llm.model_name != model:
                raise ValueError("Unexpected model configuration.")
            llm = ObservedChatModel(delegate=llm, trace=trace, role="primary")
        benchmarks[model] = EvidenceSelectionBenchmark(llm=llm)
        traces[model] = trace
    report: dict[str, Any] = {
        "purpose": "auxiliary_groundedness_model_comparison_12_cases_not_72_independent_cases",
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": None,
        "fixtures_sha256": fixture_hash,
        "prompt_sha256": prompt_hash,
        "schema_sha256": hashlib.sha256(
            json.dumps(
                ContextAssessment.provider_response_format(), sort_keys=True
            ).encode()
        ).hexdigest(),
        "models": list(models),
        "repetitions": list(REPETITIONS),
        "temperature": 0.2,
        "configured_provider": settings.llm.provider,
        "configured_fallback_enabled": settings.llm.enable_fallback,
        "configured_fallback_model": settings.openrouter.chat_model,
        "model_timeout_seconds": settings.llm.timeout_seconds,
        "benchmark_timeout_seconds": 30,
        "execution_order": "Repetition, then fixed case order; first model alternates with (case_index + repetition - 1) parity. Unit order never changes.",
        "unit_order_by_case": {
            case.id: [unit.id for unit in case.units] for case in cases
        },
        "messages_sha256_by_case": {
            case.id: hashlib.sha256(
                json.dumps(
                    [
                        {"role": message.type, "content": message.content}
                        for message in build_selector_messages(case)
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            for case in cases
        },
        "calls": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    for sequence, (repetition, case, model) in enumerate(
        execution_schedule(cases, models), start=1
    ):
        trace = traces[model]
        trace.reset()
        result = await benchmarks[model].evaluate_case(case)
        record = asdict(result)
        record.update(
            sequence=sequence,
            repetition=repetition,
            requested_model=model,
            limitation=trace.limitation,
            has_decoded_limitation=trace.has_decoded_limitation,
            input_tokens=trace.input_tokens,
            output_tokens=trace.output_tokens,
            provider_attempts=list(trace.attempts),
            fallback_used=any(
                attempt["role"] == "fallback" for attempt in trace.attempts
            ),
        )
        record["is_comparable"] = is_comparable(record)
        report["calls"].append(record)
        output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if sequence % 12 == 0:
            print(
                json.dumps(
                    {"completed": sequence, "total": 72, "repetition": repetition}
                ),
                flush=True,
            )
    report["summaries"] = build_summaries(cases, report["calls"], models)
    report["completed_at"] = datetime.now(UTC).isoformat()
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"completed": len(report["calls"]), "output": str(output)}),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-provider-requests", action="store_true")
    parser.add_argument(
        "--models",
        nargs=2,
        choices=("sabiazinho-4", "sabia-4", "sabia-4-thinking"),
        default=MODELS,
    )
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_FIXTURES.with_name("evidence_selection_base_results.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if not arguments.allow_provider_requests:
        parser.error(
            "Explicit authorization flag required for 72 provider invocations."
        )
    asyncio.run(
        run_comparison(
            fixtures=arguments.fixtures,
            baseline=arguments.baseline,
            output=arguments.output,
            models=tuple(arguments.models),
        )
    )


if __name__ == "__main__":
    main()
