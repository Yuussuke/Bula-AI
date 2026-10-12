"""End-to-end offline packages from fictional integrity fixtures, not clinical data."""

from collections import Counter
import json
from pathlib import Path
import socket
from typing import Any

import pytest

from evaluation.artifacts import digest_file, digest_value, write_new_json
from evaluation.mapping_sources import FrozenMappingSources
from evaluation.mapping_review import HumanMappingLedger
from evaluation.prepare_mapping import MappingPackageBuilder


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*arguments: object, **keywords: object) -> None:
        raise AssertionError("Network prohibited during offline mapping")

    monkeypatch.setattr(socket.socket, "connect", fail_network)
    monkeypatch.setattr(socket.socket, "connect_ex", fail_network)


ORIGINAL_SOCKET_CONNECT = socket.socket.connect


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


@pytest.fixture
def source_files(
    tmp_path: Path, request: pytest.FixtureRequest
) -> tuple[Path, Path, Path, str]:
    documents, records, bindings, wording, annotations, effective = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    golden_directory = tmp_path / "docs/evaluation/golden_set/frozen/v1"
    golden_directory.mkdir(parents=True)
    derived_directory = tmp_path / "derived/frozen/v1"
    derived_directory.mkdir(parents=True)
    index_root = tmp_path / "ingestion"
    versions = (
        "native_markdown_identity_prose_v4",
        "native_markdown_layout_regions_v5",
        "native_markdown_table_continuation_v6",
    )
    for document_index in range(100):
        corpus = "A" if document_index < 50 else "B"
        number = document_index % 50
        identifier = f"D{number:03}"
        pdf = tmp_path / f"{corpus}-{identifier}.pdf"
        pdf.write_bytes(
            f"Fictional PDF identity fixture {corpus}/{identifier}".encode()
        )
        document = {
            "corpus_id": corpus,
            "document_id": identifier,
            "sha256": digest_file(pdf),
            "path": pdf.relative_to(tmp_path).as_posix(),
        }
        documents.append(document)
        for question_index in range(10):
            question_id = f"{corpus}-{identifier}-Q{question_index:02}"
            answerable = question_index < 8
            record = {
                "question_id": question_id,
                "corpus_id": corpus,
                "document_id": identifier,
                "document_sha256": document["sha256"],
                "draft_revision": 1,
                "answerable": answerable,
                "question_scoped": "Como guardar o produto?",
                "question_cross_bula": f"Como guardar o produto fictício {corpus}-{identifier}?",
                "medication": "Fictional fixture, not a medication",
                "expected_information": "Conservar entre 15 °C e 30 °C, protegido da luz."
                if answerable
                else None,
                "required_qualifiers": ["Proteção da luz"] if answerable else [],
                "reference_evidence": [
                    {
                        "quote": "Conservar entre 15 °C e 30 °C, protegido da luz.",
                        "pdf_page": 1,
                        "section": "Conservação",
                    }
                ]
                if answerable
                else [],
                "absence_rationale": None
                if answerable
                else "Fictional absent-support fixture",
                "review_flags": [],
            }
            records.append(record)
            bindings.append(
                {
                    "question_id": question_id,
                    "record_sha256": digest_value(record),
                    "draft_revision": 1,
                    "effective_path": "docs/evaluation/golden_set/frozen/v1/records.jsonl",
                }
            )
            selected = question_index == 0 or (
                question_index == 8 if number < 20 else question_index == 1
            )
            if selected:
                entry = {
                    "question_id": question_id,
                    "source_record_sha256": digest_value(record),
                    "source_revision": 1,
                    "derived_revision": 1,
                    "question_scoped": record["question_scoped"],
                    "question_cross_bula": record["question_cross_bula"],
                    "author_language_style": "everyday",
                    "author_equivalence_note": "Fictional identity fixture only",
                }
                wording.append(entry)
                annotations.append(
                    {
                        "question_id": question_id,
                        "record_sha256": digest_value(
                            {"source": record, "derived": entry}
                        ),
                        "decision": "approved",
                        "required_information": "Fictional essential annotation"
                        if answerable
                        else "",
                        "complementary_information": "",
                        "justification": "Synthetic test, not an actual human decision",
                    }
                )
        total_chunk_count = getattr(request, "param", 2680)
        chunk_count = total_chunk_count - 99 * 26 if document_index == 99 else 26
        doc_id = f"fictional-{corpus}-{identifier}"
        chunk_directory = index_root / corpus / "debug" / identifier
        chunk_directory.mkdir(parents=True)
        chunk_path = chunk_directory / "chunks.json"
        rows = [
            {
                "chunk_id": f"{doc_id}_{index}",
                "doc_id": doc_id,
                "index": index,
                "text": "Conservar entre 15 °C e 30 °C, protegido da luz."
                if index == 0
                else f"Distrator fictício para teste de integridade número {index}",
                "section_title": "Conservação" if index == 0 else "Outra seção",
                "chunk_title": "Fictional",
                "method": "primary",
                "metadata": {"content_role": "evidence"},
            }
            for index in range(chunk_count)
        ]
        write_new_json(chunk_path, {"doc_id": doc_id, "chunks": rows})
        markdown = chunk_directory / "parsed_markdown.md"
        markdown.write_text("\n\n".join(row["text"] for row in rows), encoding="utf-8")
        checkpoint = {
            "bula_id": doc_id,
            "pdf_sha256": document["sha256"],
            "parser_version": versions[document_index % 3],
            "chunk_count": chunk_count,
            "chunks_sha256": digest_file(chunk_path),
            "markdown_sha256": digest_file(markdown),
            "chunks_path": chunk_path.relative_to(index_root).as_posix(),
            "status": "ingested_integrity_verified_not_mapping_approved",
            "fallback": {"count": 0},
        }
        checkpoint_path = index_root / corpus / f"{identifier}.json"
        write_new_json(checkpoint_path, checkpoint)
        effective.append(
            {
                **{
                    name: checkpoint[name]
                    for name in (
                        "bula_id",
                        "pdf_sha256",
                        "parser_version",
                        "chunk_count",
                        "chunks_sha256",
                        "markdown_sha256",
                    )
                },
                "corpus": corpus,
                "document_id": identifier,
                "checkpoint": checkpoint_path.relative_to(tmp_path).as_posix(),
                "checkpoint_sha256": digest_file(checkpoint_path),
            }
        )
    record_path = golden_directory / "records.jsonl"
    write_jsonl(record_path, records)
    binding_path = golden_directory / "bindings.jsonl"
    write_jsonl(binding_path, bindings)
    golden = {
        "status": "methodologically_accepted_frozen",
        "effective_inputs": [
            {
                "path": record_path.relative_to(tmp_path).as_posix(),
                "sha256": digest_file(record_path),
                "record_count": 1000,
            }
        ],
        "effective_records_fingerprint_sha256": digest_value(records),
        "record_bindings_path": binding_path.relative_to(tmp_path).as_posix(),
        "pdfs": documents,
        "counts": {
            "records": 1000,
            "pdfs": 100,
            "per_pdf": {"positive": 8, "negative": 2},
        },
    }
    golden["manifest_fingerprint_sha256"] = digest_value(golden)
    golden_path = golden_directory / "manifest.json"
    write_new_json(golden_path, golden)
    derived_wording = {
        "entries": wording,
        "source_manifest_sha256": digest_file(golden_path),
        "source_fingerprint_sha256": golden["manifest_fingerprint_sha256"],
    }
    derived_wording["fingerprint_sha256"] = digest_value(derived_wording)
    write_new_json(derived_directory / "questions.manifest.json", derived_wording)
    write_jsonl(derived_directory / "human_annotations.jsonl", annotations)
    write_new_json(
        derived_directory / "protocol.json", {"scope": "fictional-test-only"}
    )
    release = {
        "status": "human_reviewed_methodologically_accepted_frozen",
        "source_golden_manifest_sha256": digest_file(golden_path),
        "dataset_fingerprint_sha256": derived_wording["fingerprint_sha256"],
        "inputs": {
            name: digest_file(derived_directory / name)
            for name in (
                "questions.manifest.json",
                "human_annotations.jsonl",
                "protocol.json",
            )
        },
        "pdf_identities": [
            {field: document[field] for field in ("corpus_id", "document_id", "sha256")}
            for document in documents
        ],
    }
    release["fingerprint_sha256"] = digest_value(release)
    derived_path = derived_directory / "manifest.json"
    write_new_json(derived_path, release)
    verification_files = {}
    for corpus in ("A", "B"):
        verification = {"successful_count": 50, "failed_count": 0}
        verification["fingerprint_sha256"] = digest_value(verification)
        path = index_root / corpus / "verification.json"
        write_new_json(path, verification)
        verification_files[corpus] = {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": digest_file(path),
        }
    snapshot = {
        "golden_manifest_sha256": digest_file(golden_path),
        "derived_manifest_sha256": digest_file(derived_path),
        "effective_documents": effective,
        "verification_files": verification_files,
        (
            "verified_chunks" if total_chunk_count == 2680 else "effective_chunk_count"
        ): total_chunk_count,
        "parser_version_distribution": dict(
            Counter(entry["parser_version"] for entry in effective)
        ),
    }
    snapshot["fingerprint_sha256"] = digest_value(snapshot)
    snapshot_path = index_root / "ingestion-snapshot.json"
    write_new_json(snapshot_path, snapshot)
    return tmp_path, derived_path, snapshot_path, snapshot["fingerprint_sha256"]


@pytest.mark.parametrize("source_files", [2680, 2699], indirect=True)
def test_complete_package_is_deterministic_read_only_and_not_human_approved(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    sources = FrozenMappingSources(*source_files)
    before = dict(sources.files)
    first = source_files[0] / "review/v1"
    second = source_files[0] / "review/v2"
    summary = MappingPackageBuilder(sources).build(first)
    assert summary["positives"] == 160
    assert summary["negatives_separate"] == 40
    assert summary["all_references_with_candidates"] == 160
    assert summary["human_confirmed_questions"] == 0
    assert summary["pending_human_review"] == 160
    MappingPackageBuilder(sources).build(second)
    assert {path.name: digest_file(path) for path in first.iterdir()} == {
        path.name: digest_file(path) for path in second.iterdir()
    }
    package = json.loads((first / "review-package.json").read_text(encoding="utf-8"))
    assert all(case["approved_chunk_ids"] == [] for case in package["cases"])
    assert all(
        case["mapping"]["semantic_review"] == "pending" for case in package["cases"]
    )
    assert all(case["gold_chunk_ids"] == [] for case in package["negatives"])
    assert len(package["chunk_catalog"]) == len(sources.details)
    assert sources.files == before
    sources.verify_unchanged()
    with pytest.raises(ValueError, match="immutable"):
        MappingPackageBuilder(sources).build(first)


def test_incorrect_snapshot_is_rejected_before_discovery(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    with pytest.raises(ValueError, match="snapshot"):
        FrozenMappingSources(*source_files[:3], "wrong-fingerprint")


def test_declared_chunk_total_must_match_all_verified_exports(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    snapshot_path = source_files[2]
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["verified_chunks"] -= 1
    snapshot.pop("fingerprint_sha256")
    snapshot["fingerprint_sha256"] = digest_value(snapshot)
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError, match="declared 100-PDF snapshot"):
        FrozenMappingSources(*source_files[:3], snapshot["fingerprint_sha256"])


def test_changed_index_export_is_rejected(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    path = source_files[0] / "ingestion/A/debug/D000/chunks.json"
    path.write_text("changed source fixture", encoding="utf-8")
    with pytest.raises(ValueError, match="Indexed export"):
        FrozenMappingSources(*source_files)


def test_changed_input_after_loading_is_rejected(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    sources = FrozenMappingSources(*source_files)
    (source_files[0] / "ingestion/A/debug/D000/parsed_markdown.md").write_text(
        "changed fixture", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="changed during"):
        sources.verify_unchanged()


def test_changed_original_pdf_is_rejected(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    (source_files[0] / "A-D000.pdf").write_bytes(b"changed fictional PDF")
    with pytest.raises(ValueError, match="Changed PDF"):
        FrozenMappingSources(*source_files)


def test_review_ui_saves_explicit_synthetic_mapping_and_round_trips_history(
    source_files: tuple[Path, Path, Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def allow_browser_loopback(connection: socket.socket, address: object) -> None:
        # Windows event loops create a local socketpair. External addresses remain
        # forbidden; this exception applies only to the headless UI test process.
        if not isinstance(address, tuple) or address[0] not in {"127.0.0.1", "::1"}:
            raise AssertionError("External network prohibited in browser QA")
        ORIGINAL_SOCKET_CONNECT(connection, address)

    monkeypatch.setattr(socket.socket, "connect", allow_browser_loopback)
    playwright = pytest.importorskip("playwright.sync_api")
    sources = FrozenMappingSources(*source_files)
    output = tmp_path / "ui-review"
    MappingPackageBuilder(sources).build(output)
    package = json.loads((output / "review-package.json").read_text(encoding="utf-8"))
    with playwright.sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch(headless=True)
        except playwright.Error as error:
            if "Executable doesn't exist" in str(error):
                pytest.skip("Playwright Chromium not installed")
            raise
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        page.route("http://**/*", lambda route: route.abort())
        page.route("https://**/*", lambda route: route.abort())
        page.goto((output / "review.html").as_uri())
        assert "0 aprovados" in page.locator("#summary").inner_text()
        page.get_by_text(
            "Revisão detalhada / ajustar os IDs / registrar ressalva", exact=True
        ).click()
        page.get_by_role("button", name="Salvar decisão", exact=True).click()
        assert "Não salvo" in page.locator("#message").inner_text()
        page.locator("#reviewer").fill("synthetic-test-only")
        page.locator('.chunk input[type="checkbox"]').first.check()
        page.get_by_label(
            "Resultado humano desta referência", exact=True
        ).select_option("complete")
        page.get_by_label(
            "Justificativa desta associação / limitação", exact=True
        ).fill("Synthetic fixture comparison, not actual human review.")
        for title in (
            "PDF-alvo e apresentação",
            "Equivalência scoped/cross",
            "Suporte semântico",
            "Contexto e população",
            "Qualificadores indispensáveis",
            "Informação necessária",
            "Relações da tabela",
        ):
            page.get_by_label(title, exact=True).select_option("yes")
        page.get_by_label("Decisão do mapeamento", exact=True).select_option("approved")
        page.get_by_label("Justificativa geral", exact=True).fill(
            "Synthetic interaction test only."
        )
        page.get_by_role("button", name="Salvar e próxima →", exact=True).click()
        assert "2/160" in page.locator("#summary").inner_text()
        assert "1 aprovados" in page.locator("#summary").inner_text()
        page.locator("#previous").click()
        assert "1/160" in page.locator("#summary").inner_text()
        assert (
            page.get_by_label("Decisão do mapeamento", exact=True).input_value()
            == "approved"
        )
        page.screenshot(path=str(tmp_path / "review-qa.png"), full_page=False)
        with page.expect_download() as download:
            page.locator("#export").click()
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        ledger = HumanMappingLedger(package)
        ledger.import_export(exported)
        assert ledger.summary()["approved"] == 1
        assert ledger.approved_ids() == {
            package["cases"][0]["question_id"]: [
                package["cases"][0]["document_chunk_ids"][0]
            ]
        }
        page.locator("#next").click()
        page.locator("#previous").click()
        assert "1/160" in page.locator("#summary").inner_text()
        # Quick approval requires an explicit action on just the current case;
        # opening the view does not inherit the earlier question approvals.
        page.locator("#next").click()
        assert "1 aprovados" in page.locator("#summary").inner_text()
        page.get_by_role(
            "button",
            name="Conferi evidências e qualificadores — aprovar e próxima",
            exact=True,
        ).click()
        assert "3/160" in page.locator("#summary").inner_text()
        assert "2 aprovados" in page.locator("#summary").inner_text()
        page.locator("#previous").click()
        assert page.get_by_role(
            "button",
            name="Conferi evidências e qualificadores — aprovar e próxima",
            exact=True,
        ).is_disabled()
        page.screenshot(path=str(tmp_path / "quick-review-qa.png"), full_page=False)
        with page.expect_download() as quick_download:
            page.locator("#export").click()
        quick_export = json.loads(
            Path(quick_download.value.path()).read_text(encoding="utf-8")
        )
        ledger.import_export(quick_export)
        assert ledger.summary()["approved"] == 2
        browser.close()


def test_presentation_refresh_preserves_data_and_old_exports(
    source_files: tuple[Path, Path, Path, str],
) -> None:
    from evaluation.refresh_mapping_review import MappingReviewRefresher

    sources = FrozenMappingSources(*source_files)
    parent = source_files[0] / "reviews/v1"
    refreshed = source_files[0] / "reviews/v2"
    MappingPackageBuilder(sources).build(parent)
    assert MappingReviewRefresher().refresh(source_files[0], parent, refreshed) == {
        "priority": 0,
        "quick": 160,
    }
    assert digest_file(parent / "review-package.json") == digest_file(
        refreshed / "review-package.json"
    )
    package = json.loads(
        (refreshed / "review-package.json").read_text(encoding="utf-8")
    )
    assert HumanMappingLedger(package).summary()["human_reviewed"] == 0
    assert digest_file(parent / "review.html") == digest_file(refreshed / "review.html")
    with pytest.raises(ValueError, match="immutable"):
        MappingReviewRefresher().refresh(source_files[0], parent, refreshed)
