"""Presentation-only queue and explicit quick approval using fictional records."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

from evaluation.artifacts import digest_value
from evaluation.mapping_review import HumanMappingDecision, HumanMappingLedger


def call_ui(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable for offline presentation test")
    script = Path(__file__).resolve().parents[3] / "evaluation/mapping_ui/review.js"
    code = (
        "const fs=require('fs'), api=require(process.argv[1]), data=JSON.parse(fs.readFileSync(0,'utf8')); "
        + action
    )
    result = subprocess.run(
        [node, "-e", code, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def fictional_record(identifier: str, status: str = "complete") -> dict[str, Any]:
    return {
        "question_id": identifier,
        "record_sha256": "fixture-record",
        "mapping": {"input_sha256": "fixture-input", "status": status},
        "references": [{"reference_id": "R01"}],
        "document_chunk_ids": ["fixture-id"],
        "risk_flags": [],
        "candidates": {
            "R01": [
                {
                    "chunk_ids": ["fixture-id"],
                    "method": "literal_token_sequence",
                    "token_coverage": 1,
                    "source_role": "source_text",
                }
            ]
        },
    }


def test_priority_order_does_not_modify_package_membership_or_original_order() -> None:
    records = [
        fictional_record("normal"),
        fictional_record("ambiguous", "ambiguous"),
        fictional_record("partial", "partial"),
        fictional_record("absent", "absent"),
    ]
    result = call_ui(
        "const ordered=api.orderCases(data.records); console.log(JSON.stringify({ordered:ordered.map(row=>row.question_id),original:data.records.map(row=>row.question_id)}));",
        {"records": records},
    )
    assert result["ordered"] == ["absent", "partial", "ambiguous", "normal"]
    assert result["original"] == [row["question_id"] for row in records]


@pytest.mark.parametrize("status", ["absent", "partial", "ambiguous"])
def test_priority_cases_never_receive_quick_approval_proposals(status: str) -> None:
    result = call_ui(
        "console.log(JSON.stringify({proposal:api.quickProposal(data.record)}));",
        {"record": fictional_record("fixture", status)},
    )
    assert result["proposal"] is None


def test_quick_proposal_is_not_a_decision_and_excludes_tangential_partial_ids() -> None:
    record = fictional_record("fixture")
    record["candidates"]["R01"].append(
        {
            "chunk_ids": ["tangential"],
            "method": "partial_token_sequences",
            "token_coverage": 0.5,
            "source_role": "source_text",
        }
    )
    result = call_ui(
        "console.log(JSON.stringify({proposal:api.quickProposal(data.record),summary:api.summarize({cases:[data.record]},[])}));",
        {"record": record},
    )
    assert result["proposal"] == [{"reference_id": "R01", "chunk_ids": ["fixture-id"]}]
    assert result["summary"]["human_reviewed"] == 0


def test_simulated_explicit_quick_approval_uses_existing_backend_contract() -> None:
    record = fictional_record("fixture")
    package = {"cases": [record]}
    package["package_sha256"] = digest_value(package)
    result = call_ui(
        "console.log(JSON.stringify({event:api.quickEvent(data.package,data.package.cases[0],'synthetic-only')}));",
        {"package": package},
    )
    ledger = HumanMappingLedger(package)
    ledger.append(HumanMappingDecision.model_validate(result["event"]))
    assert ledger.approved_ids() == {"fixture": ["fixture-id"]}
    assert ledger.events[0].checks["table_relationships"] == "not_applicable"


def test_metadata_only_or_multiple_full_alternatives_disable_quick_mode() -> None:
    record = fictional_record("fixture")
    record["candidates"]["R01"][0]["source_role"] = (
        "metadata_requires_source_confirmation"
    )
    result = call_ui(
        "console.log(JSON.stringify({proposal:api.quickProposal(data.record)}));",
        {"record": record},
    )
    assert result["proposal"] is None
    record = fictional_record("fixture")
    record["candidates"]["R01"].append(dict(record["candidates"]["R01"][0]))
    result = call_ui(
        "console.log(JSON.stringify({proposal:api.quickProposal(data.record)}));",
        {"record": record},
    )
    assert result["proposal"] is None
