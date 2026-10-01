"""One frozen paraphrase per existing scenario; evaluation only, never chat code."""

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.modules.rag.chain import EVIDENCE_SELECTION_PROMPT
from app.modules.rag.context_assessment import ContextAssessment
from scripts.benchmark_evidence_selection import (
    EvidenceSelectionBenchmark,
    EvidenceSelectionCase,
    build_selector_messages,
    load_cases,
)
from scripts.compare_evidence_selection_models import (
    CallTrace,
    ObservedChatModel,
    is_comparable,
    summarize_calls,
)


def prepare_pairs(
    cases: list[EvidenceSelectionCase], annotations: list[dict[str, str]]
) -> list[tuple[EvidenceSelectionCase, EvidenceSelectionCase]]:
    """Reject drift before making any request; annotations never enter messages."""
    if len(cases) != 12 or len(annotations) != 12:
        raise ValueError(
            "Exactly the existing 12 scenarios and 12 paraphrases required."
        )
    pairs = []
    for original, annotation in zip(cases, annotations, strict=True):
        if (
            annotation["case_id"] != original.id
            or annotation["original_question"] != original.question
            or not annotation["review"].strip()
            or not annotation["paraphrase"].strip()
            or annotation["paraphrase"] == original.question
        ):
            raise ValueError("The reviewed manifest does not match the frozen cases.")
        paraphrase = original.model_copy(update={"question": annotation["paraphrase"]})
        if original.model_dump(exclude={"question"}) != paraphrase.model_dump(
            exclude={"question"}
        ):
            raise ValueError("Only the question may differ.")
        original_messages = build_selector_messages(original)
        variant_messages = build_selector_messages(paraphrase)
        if len(original_messages) != len(variant_messages):
            raise ValueError("Message structure changed.")
        for original_message, variant_message in zip(
            original_messages, variant_messages, strict=True
        ):
            expected = original_message.model_copy(
                update={
                    "content": str(original_message.content).replace(
                        original.question, paraphrase.question
                    )
                }
            )
            if expected.model_dump() != variant_message.model_dump():
                raise ValueError("Messages changed beyond the question substitution.")
        pairs.append((original, paraphrase))
    return pairs


async def run_comparison(
    *, fixtures: Path, paraphrases: Path, baseline: Path, output: Path
) -> None:
    from app.core.config import get_settings
    from app.modules.rag.llm import TransientFallbackChatModel, get_llm

    if output.exists():
        raise ValueError("Use a new output path; never overwrite a previous round.")
    baseline_report = json.loads(baseline.read_text(encoding="utf-8"))
    annotations = json.loads(paraphrases.read_text(encoding="utf-8"))
    cases = load_cases(fixtures)
    pairs = prepare_pairs(cases, annotations)
    prompt_text = "\n".join(
        str(message.content)
        for message in EVIDENCE_SELECTION_PROMPT.invoke(
            {"question": "", "context": "", "chat_history": []}
        ).to_messages()
    )
    hashes = {
        "fixtures_sha256": hashlib.sha256(fixtures.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
        "schema_sha256": hashlib.sha256(
            json.dumps(
                ContextAssessment.provider_response_format(), sort_keys=True
            ).encode()
        ).hexdigest(),
    }
    if any(value != baseline_report[key] for key, value in hashes.items()):
        raise ValueError("Fixtures, prompt or schema differ from model comparison.")
    for case in cases:
        messages_hash = hashlib.sha256(
            json.dumps(
                [
                    {"role": message.type, "content": message.content}
                    for message in build_selector_messages(case)
                ],
                ensure_ascii=False,
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if messages_hash != baseline_report["messages_sha256_by_case"][case.id]:
            raise ValueError("Formatted original messages differ from the baseline.")
    settings = get_settings()
    if (
        settings.llm.provider != baseline_report["configured_provider"]
        or settings.llm.enable_fallback
        != baseline_report["configured_fallback_enabled"]
        or settings.openrouter.chat_model
        != baseline_report["configured_fallback_model"]
        or settings.llm.timeout_seconds != baseline_report["model_timeout_seconds"]
    ):
        raise ValueError("Provider configuration differs from model comparison.")
    llm = get_llm(settings=settings.model_copy(update={"maritaca_model": "sabia-4"}))
    primary = llm.primary if isinstance(llm, TransientFallbackChatModel) else llm
    if primary.temperature != 0.2 or primary.model_name != "sabia-4":
        raise ValueError("Unexpected model or temperature.")
    trace = CallTrace()
    if isinstance(llm, TransientFallbackChatModel):
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
        llm = ObservedChatModel(delegate=llm, trace=trace, role="primary")
    benchmark = EvidenceSelectionBenchmark(llm=llm)
    report: dict[str, Any] = {
        "purpose": "auxiliary_paraphrase_robustness_12_scenarios_not_24_independent_cases",
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": None,
        **hashes,
        "paraphrases_sha256": hashlib.sha256(paraphrases.read_bytes()).hexdigest(),
        "comparison_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "requested_model": "sabia-4",
        "temperature": 0.2,
        "execution_order": "One original/paraphrase pair per case. Original first for odd-numbered cases, paraphrase first for even-numbered cases. Unit order unchanged.",
        "annotations_not_sent_to_model": annotations,
        "unit_order_by_case": {
            case.id: [unit.id for unit in case.units] for case in cases
        },
        "calls": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    for case_index, (original, paraphrase) in enumerate(pairs):
        variants = [("original", original), ("paraphrase", paraphrase)]
        if case_index % 2:
            variants.reverse()
        for variant, case in variants:
            trace.reset()
            record = asdict(await benchmark.evaluate_case(case))
            record.update(
                sequence=len(report["calls"]) + 1,
                variant=variant,
                requested_model="sabia-4",
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
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        print(json.dumps({"completed": len(report["calls"]), "total": 24}), flush=True)
    report["summaries"] = {
        variant: summarize_calls(
            [call for call in report["calls"] if call["variant"] == variant]
        )
        for variant in ("original", "paraphrase")
    }
    report["completed_at"] = datetime.now(UTC).isoformat()
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-provider-requests", action="store_true")
    for name in ("fixtures", "paraphrases", "baseline", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    arguments = parser.parse_args()
    if not arguments.allow_provider_requests:
        parser.error("Explicit authorization required for 24 provider invocations.")
    asyncio.run(
        run_comparison(
            fixtures=arguments.fixtures,
            paraphrases=arguments.paraphrases,
            baseline=arguments.baseline,
            output=arguments.output,
        )
    )


if __name__ == "__main__":
    main()
