"""Offline discovery and human event invariants; fixtures are not actual decisions."""

from dataclasses import replace
from pathlib import Path
import json
import shutil
import subprocess

import pytest

from evaluation.artifacts import digest_value
from evaluation.contracts import EvidenceReference, MappingInput, SnapshotChunk
from evaluation.dataset import DocumentIdentity
from evaluation.evidence_mapping import EvidenceCandidateMapper, tokens
from evaluation.mapping_review import (
    HumanMappingDecision,
    HumanMappingLedger,
    REVIEW_CHECKS,
)
from evaluation.prepare_mapping import (
    MappingPackageBuilder,
    documentary_region_text,
    documentary_presence,
    candidate_has_recorded_fallback,
)


def mapping_input(texts: tuple[str, ...], quotes: tuple[str, ...]) -> MappingInput:
    document = DocumentIdentity("A", "D1", "pdf-hash", "original.pdf")
    return MappingInput(
        "Q1",
        "record-hash",
        "snapshot-file-hash",
        document,
        "Como guardar?",
        "Como guardar Produto X?",
        "15 a 30 °C",
        ("Proteção da luz",),
        tuple(
            EvidenceReference(f"R{index}", quote, 2, "Conservação")
            for index, quote in enumerate(quotes)
        ),
        tuple(
            SnapshotChunk(f"chunk{index}", document, text, "Conservação")
            for index, text in enumerate(texts)
        ),
    )


def package_fixture() -> dict:
    package = {
        "cases": [
            {
                "question_id": "Q1",
                "record_sha256": "record-hash",
                "mapping": {"input_sha256": "input-hash"},
                "references": [{"reference_id": "R0"}],
                "document_chunk_ids": ["chunk0", "chunk1"],
                "risk_flags": [],
            }
        ],
        "negatives": [],
    }
    package["package_sha256"] = digest_value(package)
    return package


def decision_fixture(package: dict) -> HumanMappingDecision:
    return HumanMappingDecision(
        question_id="Q1",
        record_sha256="record-hash",
        input_sha256="input-hash",
        package_sha256=package["package_sha256"],
        reviewer_id="synthetic-test-only",
        reviewed_at="2026-10-12T12:00:00Z",
        decision="approved",
        checks={key: "yes" for key in REVIEW_CHECKS},
        references=[
            {
                "reference_id": "R0",
                "chunk_ids": ["chunk0"],
                "status": "complete",
                "rationale": "Synthetic source and scope verified.",
            }
        ],
        justification="Synthetic test, never an actual human approval.",
    )


def test_literal_match_does_not_approve_semantic_support() -> None:
    value = mapping_input(
        ("Conservar entre 15 °C e 30 °C, protegido da luz.",),
        ("Conservar entre 15 °C e 30 °C",),
    )
    output, candidates = EvidenceCandidateMapper().discover(value)
    assert output.status == "complete"
    assert output.semantic_review == "pending"
    assert candidates["R0"][0].chunk_ids == ("chunk0",)
    assert value.chunks[0].text.endswith("protegido da luz.")


def test_ordered_fragmented_quote_uses_multiple_real_ids() -> None:
    value = mapping_input(
        ("Não utilizar o produto", "durante o terceiro trimestre da gravidez."),
        ("Não utilizar o produto durante o terceiro trimestre da gravidez.",),
    )
    output, candidates = EvidenceCandidateMapper().discover(value)
    assert output.status == "complete"
    assert any(
        candidate.chunk_ids == ("chunk0", "chunk1")
        and candidate.method == "adjacent_literal_token_sequence"
        for candidate in candidates["R0"]
    )


def test_duplicate_full_quotes_are_reviewable_alternatives() -> None:
    value = mapping_input(
        ("Conservar entre 15 °C e 30 °C.", "Conservar entre 15 °C e 30 °C."),
        ("Conservar entre 15 °C e 30 °C.",),
    )
    output, _ = EvidenceCandidateMapper().discover(value)
    assert output.status == "ambiguous"
    assert output.matches[0].chunk_ids == ("chunk0", "chunk1")


def test_one_missing_reference_keeps_question_in_denominator() -> None:
    value = mapping_input(
        ("Conservar entre 15 °C e 30 °C.",),
        ("Conservar entre 15 °C e 30 °C.", "Proteger da umidade."),
    )
    output, _ = EvidenceCandidateMapper().discover(value)
    assert output.status == "partial"
    assert len(output.matches) == 2
    assert output.matches[1].status == "absent"
    assert output.matches[1].chunk_ids == ()


def test_metadata_literal_is_not_automatically_complete_source_support() -> None:
    value = mapping_input(
        ('---\npresentation: "Comprimidos de 10 mg"\n---',), ("Comprimidos de 10 mg",)
    )
    output, candidates = EvidenceCandidateMapper().discover(value)
    assert output.status == "partial"
    assert candidates["R0"][0].source_role == "metadata_requires_source_confirmation"


def test_related_topic_alone_does_not_create_a_match() -> None:
    value = mapping_input(
        ("O produto é usado para tratamento de sintomas nasais.",),
        ("Pacientes com insuficiência renal grave não devem utilizar.",),
    )
    output, candidates = EvidenceCandidateMapper().discover(value)
    assert output.status == "absent"
    assert not candidates["R0"]


def test_units_values_and_order_are_not_semantically_converted() -> None:
    assert tokens("25 mg/mL") != tokens("25 mEq/L")
    assert tokens("1,5") != tokens("15")
    value = mapping_input(
        ("| Idade | Volume |\n| Adulto | 10 mL |",),
        ("| Idade | Volume |\n| Adulto | 5 mL |",),
    )
    output, _ = EvidenceCandidateMapper().discover(value)
    assert output.status != "complete"


def test_foreign_document_chunks_rejected() -> None:
    value = mapping_input(("Texto",), ("Texto",))
    foreign = replace(
        value.chunks[0], document=DocumentIdentity("B", "D1", "another", "other.pdf")
    )
    with pytest.raises(ValueError, match="another PDF"):
        EvidenceCandidateMapper().discover(replace(value, chunks=(foreign,)))


def test_structured_source_region_is_not_flattened_or_discarded() -> None:
    region = [10, 20, 30, 40]
    assert json.loads(documentary_region_text(region) or "null") == region
    assert documentary_region_text("table row 3") == "table row 3"
    assert documentary_region_text(None) is None


def test_metadata_presence_is_not_reported_as_missing_index_content() -> None:
    assert (
        documentary_presence(True, True, False)
        == "literal_in_metadata_only_requires_documentary_confirmation"
    )
    assert (
        documentary_presence(True, False, False)
        == "source_quote_in_markdown_without_full_chunk_correspondence"
    )


def test_fallback_origin_uses_recorded_reason_not_a_nonexistent_method() -> None:
    assert candidate_has_recorded_fallback(
        {
            "method": "deterministic",
            "metadata": {"fallback_reason": "split_table_context"},
        }
    )
    assert not candidate_has_recorded_fallback(
        {"method": "primary", "metadata": {"validation_outcome": "passed"}}
    )


def test_human_ledger_starts_pending_without_inheriting_question_approval() -> None:
    ledger = HumanMappingLedger(package_fixture())
    assert ledger.summary()["human_reviewed"] == 0
    assert ledger.summary()["pending"] == 1
    assert ledger.approved_ids() == {}


@pytest.mark.parametrize(
    "field,value",
    [
        ("record_sha256", "old"),
        ("input_sha256", "other"),
        ("package_sha256", "stale"),
        ("reviewed_at", "2026-10-12T12:00:00"),
    ],
)
def test_stale_or_unbound_decision_rejected(field: str, value: str) -> None:
    package = package_fixture()
    event = decision_fixture(package).model_copy(update={field: value})
    with pytest.raises(ValueError):
        HumanMappingLedger(package).append(event)


def test_human_mapping_cannot_select_foreign_chunk() -> None:
    package = package_fixture()
    data = decision_fixture(package).model_dump()
    data["references"][0]["chunk_ids"] = ["foreign"]
    with pytest.raises(ValueError, match="foreign"):
        HumanMappingLedger(package).append(HumanMappingDecision.model_validate(data))


def test_doubtful_approval_rejected_but_pending_event_preserved() -> None:
    package = package_fixture()
    event = decision_fixture(package)
    event.checks["semantic_support"] = "doubt"
    ledger = HumanMappingLedger(package)
    with pytest.raises(ValueError, match="doubtful"):
        ledger.append(event)
    ledger.append(event.model_copy(update={"decision": "pending"}))
    assert ledger.summary()["with_doubts"] == 1
    assert ledger.approved_ids() == {}


def test_partial_and_absent_support_cannot_be_approved() -> None:
    package = package_fixture()
    event = decision_fixture(package)
    event.references[0].status = "partial"
    with pytest.raises(ValueError, match="sufficient"):
        HumanMappingLedger(package).append(event)


def test_table_relations_cannot_be_declared_not_applicable() -> None:
    package = package_fixture()
    package["cases"][0]["risk_flags"] = ["table"]
    package.pop("package_sha256")
    package["package_sha256"] = digest_value(package)
    event = decision_fixture(package)
    event.checks["table_relationships"] = "not_applicable"
    with pytest.raises(ValueError, match="Table"):
        HumanMappingLedger(package).append(event)


def test_export_is_append_only_and_same_gold_ids_apply_to_both_scenarios() -> None:
    package = package_fixture()
    ledger = HumanMappingLedger(package)
    event = decision_fixture(package)
    ledger.append(event)
    exported = {
        "schema_version": 1,
        "package_sha256": package["package_sha256"],
        "events": [event.model_dump()],
        "summary": ledger.summary(),
    }
    restored = HumanMappingLedger(package)
    restored.import_export(exported)
    assert restored.approved_ids() == {"Q1": ["chunk0"]}
    with pytest.raises(ValueError, match="remove history"):
        restored.import_export(
            {**exported, "events": [], "summary": HumanMappingLedger(package).summary()}
        )


def test_html_escapes_source_text_and_has_no_automatic_decisions(
    tmp_path: Path,
) -> None:
    package = package_fixture()
    package["unsafe_source_fixture"] = "</script><script>alert(1)</script>"
    MappingPackageBuilder._render(tmp_path, package)
    html = (tmp_path / "review.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)</script>" not in html
    assert "\\u003c/script>" in html
    assert "let events = []" in html
    assert "fetch(" not in html


def test_browser_event_validation_matches_backend(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable for offline UI contract test")
    package = package_fixture()
    event = decision_fixture(package).model_dump()
    javascript = Path(__file__).resolve().parents[3] / "evaluation/mapping_ui/review.js"
    program = "const fs=require('fs'); const api=require(process.argv[1]); const input=JSON.parse(fs.readFileSync(0,'utf8')); api.validateEvent(input.package,input.event); console.log(JSON.stringify(api.summarize(input.package,[input.event])));"
    result = subprocess.run(
        [node, "-e", program, str(javascript)],
        input=json.dumps({"package": package, "event": event}),
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout)["approved"] == 1
    event["references"][0]["chunk_ids"] = ["foreign"]
    rejected = subprocess.run(
        [node, "-e", program, str(javascript)],
        input=json.dumps({"package": package, "event": event}),
        text=True,
        capture_output=True,
    )
    assert rejected.returncode != 0
