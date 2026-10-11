from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
import socket
from typing import Any

import pytest

from evaluation.artifacts import digest_file, digest_value, write_new_json
from evaluation.contracts import (
    EvidenceReference,
    MappingInput,
    MappingOutput,
    RankedChunk,
    ReferenceMatch,
    RetrievalJob,
    RetrievalRequest,
    SnapshotChunk,
)
from evaluation.dataset import DocumentIdentity, FrozenCollection
from evaluation.runner import OfflineRetrievalRunner, plan_retrieval_jobs
from evaluation.snapshot import read_declared_settings


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*arguments: object, **keywords: object) -> None:
        raise AssertionError("Network is prohibited in offline tests")

    monkeypatch.setattr(socket, "socket", fail_network)


@pytest.fixture
def collection(tmp_path: Path) -> FrozenCollection:
    documents: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for corpus_id in ("A", "B"):
        pdf = tmp_path / f"{corpus_id}.pdf"
        pdf.write_bytes(f"synthetic document {corpus_id}".encode())
        documents.append(
            {
                "corpus_id": corpus_id,
                "document_id": "D1",
                "sha256": digest_file(pdf),
                "path": pdf.name,
            }
        )
        for number, answerable in ((1, True), (2, False)):
            records.append(
                {
                    "question_id": f"{corpus_id}-D1-Q{number}",
                    "draft_revision": 1,
                    "corpus_id": corpus_id,
                    "document_id": "D1",
                    "document_sha256": digest_file(pdf),
                    "answerable": answerable,
                    "question_scoped": f"Pergunta {number}?",
                    "question_cross_bula": f"Pergunta {number} sobre {corpus_id}?",
                    "human_review_status": "pending",
                }
            )
    input_path = tmp_path / "base.jsonl"
    import json

    input_path.write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )
    bindings = [
        {
            "question_id": record["question_id"],
            "draft_revision": 1,
            "record_sha256": digest_value(record),
            "effective_path": input_path.name,
        }
        for record in records
    ]
    (tmp_path / "bindings.jsonl").write_text(
        "\n".join(json.dumps(binding) for binding in bindings), encoding="utf-8"
    )
    manifest = {
        "status": "methodologically_accepted_frozen",
        "effective_inputs": [
            {
                "path": input_path.name,
                "sha256": digest_file(input_path),
                "record_count": 4,
            }
        ],
        "effective_records_fingerprint_sha256": digest_value(records),
        "record_bindings_path": "bindings.jsonl",
        "pdfs": documents,
        "counts": {"records": 4, "pdfs": 2, "per_pdf": {"positive": 1, "negative": 1}},
    }
    manifest["manifest_fingerprint_sha256"] = digest_value(manifest)
    write_new_json(tmp_path / "manifest.json", manifest)
    return FrozenCollection(tmp_path, tmp_path / "manifest.json")


def test_plan_separates_retrieval_from_negatives_and_preserves_cross_query(
    collection: FrozenCollection,
) -> None:
    jobs = plan_retrieval_jobs(collection)
    assert len(jobs) == 12
    assert len({job.key for job in jobs}) == 12
    assert {job.scenario for job in jobs} == {"scoped", "cross"}
    for job in jobs:
        assert job.question_id.endswith("Q1")
        if job.scenario == "cross":
            assert job.request().scoped_document_id is None
            assert (
                job.request().question
                == collection.records[job.question_id]["question_cross_bula"]
            )
        else:
            assert job.request().scoped_document_id == "D1"
    assert all(
        record["human_review_status"] == "pending"
        for record in collection.records.values()
    )


@pytest.mark.parametrize("defect", ["missing", "foreign", "changed", "duplicate"])
def test_universe_rejects_contamination_before_search(
    collection: FrozenCollection, defect: str
) -> None:
    universe = collection.universe("A")
    if defect == "missing":
        broken = ()
    elif defect == "foreign":
        broken = universe + collection.universe("B")
    elif defect == "changed":
        broken = (replace(universe[0], pdf_sha256="wrong"),)
    else:
        broken = universe + universe
    with pytest.raises(ValueError, match="Index universe"):
        collection.validate_index_universe("A", broken)


def test_pdf_and_record_changes_are_detected(collection: FrozenCollection) -> None:
    collection.verify_pdf_hashes()
    (collection.root / "A.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Changed PDF"):
        collection.verify_pdf_hashes()
    (collection.root / "base.jsonl").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="Changed frozen input"):
        FrozenCollection(collection.root, collection.manifest_path)


class FixtureRetriever:
    is_offline = True

    def __init__(
        self, ranking: tuple[RankedChunk, ...], has_failure: bool = False
    ) -> None:
        self.ranking = ranking
        self.has_failure = has_failure
        self.requests: list[RetrievalRequest] = []

    def retrieve(
        self, request: RetrievalRequest, strategy: str
    ) -> tuple[RankedChunk, ...]:
        self.requests.append(request)
        if self.has_failure:
            raise TimeoutError("sensitive provider body must not be exported")
        return self.ranking


def runner(
    collection: FrozenCollection,
    tmp_path: Path,
    jobs: tuple[RetrievalJob, ...] | None = None,
    snapshot: str = "snapshot-v1",
) -> OfflineRetrievalRunner:
    return OfflineRetrievalRunner(
        checkpoint_path=tmp_path / "checkpoint.jsonl",
        snapshot_sha256=snapshot,
        universe=collection.documents,
        jobs=jobs or (plan_retrieval_jobs(collection)[0],),
    )


def ranked(
    document: DocumentIdentity, chunk_id: str = "c1", rank: int = 1
) -> RankedChunk:
    return RankedChunk(
        chunk_id,
        document.document_id,
        document.corpus_id,
        document.pdf_sha256,
        "text-hash",
        rank,
        1.0,
        {"bm25_score": 1.0},
    )


def test_resume_preserves_ranking_scores_and_does_not_rerun(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    adapter = FixtureRetriever((ranked(collection.universe("A")[0]),))
    first = runner(collection, tmp_path).run(adapter)
    second = runner(collection, tmp_path).run(adapter)
    assert first == second
    assert len(adapter.requests) == 1
    assert second[0]["ranking"][0]["score_details"] == {"bm25_score": 1.0}
    assert second[0]["ranking"][0]["text_sha256"] == "text-hash"
    assert "gold_ids" not in second[0]


def test_empty_ranking_is_not_technical_failure(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    result = runner(collection, tmp_path).run(FixtureRetriever(()))[0]
    assert result["status"] == "success"
    assert result["ranking"] == []
    assert result["technical_failure"] is None


def test_failure_is_preserved_without_retry_or_sensitive_body(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    adapter = FixtureRetriever((), has_failure=True)
    first = runner(collection, tmp_path).run(adapter)
    assert first[0]["status"] == "technical_failure"
    assert first[0]["technical_failure"] == "TimeoutError"
    assert first[0]["failure_stage"] == "retrieval"
    assert first[0]["ranking"] is None
    assert "sensitive" not in (tmp_path / "checkpoint.jsonl").read_text()
    assert runner(collection, tmp_path).run(adapter) == first
    assert len(adapter.requests) == 1


def test_changed_snapshot_or_record_blocks_resume(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    adapter = FixtureRetriever(())
    instance = runner(collection, tmp_path)
    instance.run(adapter)
    with pytest.raises(ValueError, match="snapshot mismatch"):
        runner(collection, tmp_path, snapshot="snapshot-v2").run(adapter)
    modified_job = replace(instance.jobs[0], record_sha256="other-version")
    with pytest.raises(ValueError, match="snapshot mismatch"):
        runner(collection, tmp_path, jobs=(modified_job,)).run(adapter)
    assert len(adapter.requests) == 1


def test_tampered_checkpoint_is_not_silently_repaired(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    instance = runner(collection, tmp_path)
    instance.run(FixtureRetriever(()))
    path = tmp_path / "checkpoint.jsonl"
    path.write_text(
        path.read_text().replace(
            '"status": "success"', '"status": "technical_failure"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="changed"):
        instance.run(FixtureRetriever(()))


def test_external_adapter_is_refused_before_any_call(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    adapter = FixtureRetriever(())
    adapter.is_offline = False
    with pytest.raises(ValueError, match="not authorized"):
        runner(collection, tmp_path).run(adapter)
    assert adapter.requests == []
    assert not (tmp_path / "checkpoint.jsonl").exists()


@pytest.mark.parametrize(
    "defect", ["foreign", "wrong_hash", "rank_gap", "duplicate", "nan"]
)
def test_bad_rankings_are_recorded_as_contract_failures(
    collection: FrozenCollection, tmp_path: Path, defect: str
) -> None:
    chunk = ranked(collection.universe("A")[0])
    ranking = (chunk,)
    if defect == "foreign":
        ranking = (ranked(collection.universe("B")[0]),)
    elif defect == "wrong_hash":
        ranking = (replace(chunk, pdf_sha256="wrong"),)
    elif defect == "rank_gap":
        ranking = (replace(chunk, rank=2),)
    elif defect == "duplicate":
        ranking = (chunk, replace(chunk, rank=2))
    else:
        ranking = (replace(chunk, score=float("nan")),)
    result = runner(collection, tmp_path).run(FixtureRetriever(ranking))[0]
    assert result["status"] == "technical_failure"
    assert result["technical_failure"] == "ValueError"
    assert result["failure_stage"] == "ranking_validation"


def test_cross_preserves_other_document_positions(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    target = collection.universe("A")[0]
    distractor = replace(target, document_id="D2", pdf_sha256="second-pdf")
    job = next(
        job
        for job in plan_retrieval_jobs(collection)
        if job.target == target and job.scenario == "cross"
    )
    instance = OfflineRetrievalRunner(
        checkpoint_path=tmp_path / "cross.jsonl",
        snapshot_sha256="snapshot",
        universe=(target, distractor),
        jobs=(job,),
    )
    adapter = FixtureRetriever((ranked(distractor), ranked(target, "c2", 2)))
    result = instance.run(adapter)[0]
    assert [row["document_id"] for row in result["ranking"]] == ["D2", "D1"]
    assert adapter.requests[0].scoped_document_id is None


def mapping_input(document: DocumentIdentity) -> MappingInput:
    return MappingInput(
        "q1",
        "record-v1",
        "ingestion-v1",
        document,
        "Pergunta?",
        "Pergunta sobre medicamento?",
        "Informação",
        ("População e apresentação",),
        (
            EvidenceReference("r1", "texto da linha", 2, "Tabela"),
            EvidenceReference("r2", "qualificador", 3, "Seção"),
        ),
        (
            SnapshotChunk(
                "c1",
                document,
                "texto da linha",
                "Tabela",
                ("Pediátrico", "Peso | Orientação"),
            ),
            SnapshotChunk("c2", document, "qualificador", "Seção"),
        ),
    )


def test_mapping_preserves_multiple_chunks_context_and_pending_semantics(
    collection: FrozenCollection,
) -> None:
    source = mapping_input(collection.documents[0])
    output = MappingOutput(
        digest_value(asdict(source)),
        "complete",
        (
            ReferenceMatch("r1", ("c1",), "complete", "literal"),
            ReferenceMatch("r2", ("c1", "c2"), "complete", "distributed"),
        ),
    )
    output.validate(source)
    assert source.chunks[0].text == "texto da linha"
    assert source.chunks[0].local_context == ("Pediátrico", "Peso | Orientação")
    assert output.semantic_review == "pending"
    assert output.matches[1].chunk_ids == ("c1", "c2")


@pytest.mark.parametrize("status", ["partial", "ambiguous", "absent"])
def test_unresolved_mapping_keeps_positive_record_and_every_reference(
    collection: FrozenCollection, status: str
) -> None:
    source = mapping_input(collection.documents[0])
    chunk_ids = () if status == "absent" else ("c1",)
    output = MappingOutput(
        digest_value(asdict(source)),
        status,
        tuple(
            ReferenceMatch(
                reference.reference_id, chunk_ids, status, "Requires conference"
            )
            for reference in source.references
        ),
    )
    output.validate(source)
    assert output.semantic_review == "pending"
    assert len(output.matches) == 2
    assert source.question_id == "q1"


def test_mapping_rejects_foreign_chunks_missing_reference_and_stale_snapshot(
    collection: FrozenCollection,
) -> None:
    source = mapping_input(collection.documents[0])
    with pytest.raises(ValueError, match="another PDF"):
        replace(
            source,
            chunks=(replace(source.chunks[0], document=collection.documents[1]),),
        ).validate()
    output = MappingOutput(
        digest_value(asdict(source)),
        "partial",
        (ReferenceMatch("r1", ("c1",), "partial", "Missing r2"),),
    )
    with pytest.raises(ValueError, match="every reference"):
        output.validate(source)
    with pytest.raises(ValueError, match="another input"):
        replace(output, input_sha256="old-snapshot").validate(source)


def test_settings_capture_does_not_execute_code_or_include_secrets(
    tmp_path: Path,
) -> None:
    path = tmp_path / "settings.py"
    from evaluation.snapshot import SETTING_FIELDS

    classes = []
    for class_name, fields in SETTING_FIELDS.items():
        classes.append(
            f"class {class_name}:\n    api_key: str = 'DO_NOT_EXPORT'\n"
            + "\n".join(f"    {name}: str = 'safe'" for name in fields)
        )
    path.write_text(
        "raise RuntimeError('must never execute')\n" + "\n".join(classes),
        encoding="utf-8",
    )
    settings = read_declared_settings(path)
    assert settings["MaritacaSettings"]["maritaca_model"] == "safe"
    assert "DO_NOT_EXPORT" not in str(settings)


def test_artifacts_cannot_overwrite_history(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    write_new_json(path, {"version": 1})
    before = digest_file(path)
    with pytest.raises(FileExistsError):
        write_new_json(path, {"version": 2})
    assert digest_file(path) == before


def test_incomplete_checkpoint_fails_without_losing_history(
    collection: FrozenCollection, tmp_path: Path
) -> None:
    instance = runner(collection, tmp_path)
    instance.run(FixtureRetriever(()))
    with instance.path.open("a", encoding="utf-8") as stream:
        stream.write('{"job_key":')
    before = digest_file(instance.path)
    import json

    with pytest.raises(json.JSONDecodeError):
        instance.run(FixtureRetriever(()))
    assert digest_file(instance.path) == before
    assert len(instance.jobs) == 1


def test_source_snapshot_detects_modified_or_added_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from evaluation.snapshot import SETTING_FIELDS, SourceSnapshot

    def fake_git_read(root: Path, *arguments: str) -> str:
        return "fixture-commit" if arguments == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr("evaluation.snapshot.git_read", fake_git_read)
    config = tmp_path / "backend/app/core/config.py"
    config.parent.mkdir(parents=True)
    config.write_text(
        "\n".join(
            f"class {name}:\n"
            + "\n".join(f"    {field}: str = 'safe'" for field in fields)
            for name, fields in SETTING_FIELDS.items()
        ),
        encoding="utf-8",
    )
    snapshot = SourceSnapshot(tmp_path).capture()
    assert snapshot["runtime_verified"] is False
    extra = config.parent / "new_component.py"
    extra.write_text("VERSION = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="files changed"):
        SourceSnapshot.verify(snapshot)
    snapshot_with_extra = SourceSnapshot(tmp_path).capture()
    extra.write_text("VERSION = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="files changed"):
        SourceSnapshot.verify(snapshot_with_extra)


def test_mapping_rejects_unknown_ids_and_concealed_partial_reference(
    collection: FrozenCollection,
) -> None:
    source = mapping_input(collection.documents[0])
    output = MappingOutput(
        digest_value(asdict(source)),
        "complete",
        (
            ReferenceMatch("r1", ("foreign-id",), "complete", "invalid"),
            ReferenceMatch("r2", ("c2",), "complete", "literal"),
        ),
    )
    with pytest.raises(ValueError, match="Unknown"):
        output.validate(source)
    partial = replace(
        output,
        matches=(
            ReferenceMatch("r1", ("c1",), "partial", "Missing qualifier"),
            output.matches[1],
        ),
    )
    with pytest.raises(ValueError, match="conceal"):
        partial.validate(source)


def test_override_evidence_excludes_credentials_and_is_not_runtime_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from evaluation.snapshot import settings_override_evidence

    (tmp_path / ".env").write_text(
        "MARITACA_API_KEY=DO_NOT_EXPORT\nSECRET_KEY=DO_NOT_EXPORT\nMARITACA_MODEL=sabia-4\nLLM_ENABLE_FALLBACK=true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "DO_NOT_EXPORT")
    monkeypatch.setenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    evidence = settings_override_evidence(tmp_path)
    assert evidence["dotenv_declarations"]["MARITACA_MODEL"] == "sabia-4"
    assert (
        evidence["tool_process_declarations"]["EMBEDDING_MODEL"]
        == "intfloat/multilingual-e5-large"
    )
    assert "DO_NOT_EXPORT" not in str(evidence)
