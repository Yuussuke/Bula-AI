"""Opt-in auxiliary selection benchmark; not the main TCC evaluation."""

import json
import os
from pathlib import Path

import pytest

from scripts.benchmark_evidence_selection import run_benchmark


@pytest.mark.anyio
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_EVIDENCE_TESTS") != "1",
    reason="Explicit opt-in required: sends frozen evidence to the configured LLM.",
)
async def test_live_selector_matches_frozen_gold_sets(tmp_path: Path) -> None:
    report = await run_benchmark()
    report_path = tmp_path / "evidence-selection-results.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"\nAuxiliary benchmark report: {report_path}\n{json.dumps(report, indent=2)}"
    )
    # Finish and report all scenarios before failing this optional exact-set check.
    aggregate = report["aggregate"]
    assert isinstance(aggregate, dict)
    assert aggregate["technical_failure_count"] == 0
    assert aggregate["exact_set_match_count"] == aggregate["attempted_cases"]
