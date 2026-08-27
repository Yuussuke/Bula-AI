import base64
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import Page
from pydantic import ValidationError

from app.modules.bulas.schemas import (
    SystemBulaManifest,
    SystemBulaManifestEntry,
    SystemBulaManifestReview,
)
from scripts import download_bulas
from scripts.download_bulas import (
    AnvisaBulaDownloader,
    AnvisaBulaRecord,
    AnvisaBulaTarget,
    AnvisaSelectionError,
    decode_source_record_id,
    parse_arguments,
)
from tests.pdf_factory import build_pdf_bytes


def build_protected_id(source_record_id: str) -> str:
    payload = (
        base64.urlsafe_b64encode(json.dumps({"jti": source_record_id}).encode())
        .decode()
        .rstrip("=")
    )
    return f"header.{payload}.signature"


def build_record(
    *,
    source_record_id: str = "111",
    product_id: int = 10,
    registration_number: str = "123456789",
    product_name: str = "DIPIRONA",
) -> AnvisaBulaRecord:
    return AnvisaBulaRecord(
        idProduto=product_id,
        numeroRegistro=registration_number,
        nomeProduto=product_name,
        expediente="987654",
        razaoSocial="EMS S/A",
        cnpj="00000000000100",
        numeroTransacao="transaction-1",
        data="2026-08-20T10:00:00-03:00",
        numProcesso="process-1",
        idBulaPacienteProtegido=build_protected_id(source_record_id),
        idBulaProfissionalProtegido=build_protected_id(f"{source_record_id}2"),
        dataAtualizacao="2026-08-21T10:00:00-03:00",
    )


def build_target(
    *,
    source_record_id: str = "111",
    product_id: int = 10,
    registration_number: str = "123456789",
    product_name: str = "DIPIRONA",
) -> AnvisaBulaTarget:
    return AnvisaBulaTarget(
        target_id="dipirona-500mg-tablet",
        search_query="Dipirona",
        active_ingredient="dipirona monoidratada",
        product_name=product_name,
        strength="500 mg",
        pharmaceutical_form="comprimido",
        presentation="caixa com 10 comprimidos",
        audience="patient",
        manufacturer="EMS S/A",
        company_tax_id="00000000000100",
        anvisa_product_id=product_id,
        registration_number=registration_number,
        process_number="process-1",
        expedition_number="987654",
        transaction_number="transaction-1",
        source_record_id=source_record_id,
        expected_pdf_terms=["Dipirona", "500 mg", "comprimido"],
    )


def build_downloader(tmp_path: Path) -> AnvisaBulaDownloader:
    return AnvisaBulaDownloader(
        page=cast(Page, object()),
        output_directory=tmp_path,
        manifest_path=tmp_path / "manifest.json",
        max_pdf_size_bytes=10 * 1024 * 1024,
    )


def approve_manifest(manifest_path: Path) -> None:
    manifest = SystemBulaManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    approved_document = manifest.documents[0].model_copy(
        update={
            "review": SystemBulaManifestReview(
                status="approved",
                reviewed_by="reviewer@example.com",
                reviewed_at=datetime.now(UTC),
            )
        }
    )
    approved_manifest = SystemBulaManifest(documents=[approved_document])
    manifest_path.write_text(
        approved_manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )


@pytest.mark.anyio
async def test_downloader_selects_exact_record_among_same_manufacturer_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_content = build_pdf_bytes("Dipirona 500 mg comprimido")
    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(
        return_value=[
            build_record(
                source_record_id="999",
                product_id=20,
                registration_number="999999999",
                product_name="DIPIRONA 1 G",
            ),
            build_record(),
        ]
    )
    download_mock = AsyncMock(return_value=pdf_content)
    monkeypatch.setattr(download_bulas, "browser_pdf", download_mock)

    results = await downloader.download_targets([build_target()])

    result = results["dipirona-500mg-tablet"]
    assert result is not None
    assert result.was_reused is False
    assert result.manifest_entry.source_record_id == "111"
    assert result.manifest_entry.registration_number == "123456789"
    assert result.manifest_entry.review.status == "pending"
    assert result.file_path.name == "dipirona-500mg-tablet__111__patient.pdf"
    assert result.file_path.read_bytes() == pdf_content
    assert not result.file_path.with_suffix(".pdf.part").exists()


@pytest.mark.anyio
async def test_downloader_reuses_only_manifest_verified_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = build_target()
    record = build_record()
    pdf_content = build_pdf_bytes("Dipirona 500 mg comprimido")
    initial_downloader = build_downloader(tmp_path)
    initial_downloader.fetch_all_results = AsyncMock(return_value=[record])
    monkeypatch.setattr(
        download_bulas,
        "browser_pdf",
        AsyncMock(return_value=pdf_content),
    )
    await initial_downloader.download_targets([target])
    approve_manifest(tmp_path / "manifest.json")

    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[record])
    download_mock = AsyncMock()
    monkeypatch.setattr(download_bulas, "browser_pdf", download_mock)
    results = await downloader.download_targets([target])

    result = results[target.target_id]
    assert result is not None
    assert result.was_reused is True
    assert result.manifest_entry.review.status == "approved"
    assert (
        result.manifest_entry.sha256_checksum == hashlib.sha256(pdf_content).hexdigest()
    )
    download_mock.assert_not_awaited()


@pytest.mark.anyio
async def test_changed_source_id_forces_fresh_download_and_pending_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_target = build_target(source_record_id="111")
    old_record = build_record(source_record_id="111")
    old_pdf = build_pdf_bytes("Dipirona 500 mg comprimido versao antiga")
    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[old_record])
    monkeypatch.setattr(
        download_bulas,
        "browser_pdf",
        AsyncMock(return_value=old_pdf),
    )
    await downloader.download_targets([old_target])
    approve_manifest(tmp_path / "manifest.json")

    new_target = build_target(source_record_id="222")
    new_record = build_record(source_record_id="222")
    new_pdf = build_pdf_bytes("Dipirona 500 mg comprimido versao atual")
    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[new_record])
    download_mock = AsyncMock(return_value=new_pdf)
    monkeypatch.setattr(download_bulas, "browser_pdf", download_mock)

    results = await downloader.download_targets([new_target])

    result = results[new_target.target_id]
    assert result is not None
    assert result.was_reused is False
    assert result.manifest_entry.source_record_id == "222"
    assert result.manifest_entry.review.status == "pending"
    assert (
        len(
            SystemBulaManifest.model_validate_json(
                (tmp_path / "manifest.json").read_text(encoding="utf-8")
            ).documents
        )
        == 1
    )
    download_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_corrupt_existing_pdf_is_replaced_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = build_target()
    record = build_record()
    valid_pdf = build_pdf_bytes("Dipirona 500 mg comprimido")
    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[record])
    monkeypatch.setattr(
        download_bulas,
        "browser_pdf",
        AsyncMock(return_value=valid_pdf),
    )
    first_result = (await downloader.download_targets([target]))[target.target_id]
    assert first_result is not None
    first_result.file_path.write_bytes(b"%PDF-1.4 partial data")

    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[record])
    monkeypatch.setattr(
        download_bulas,
        "browser_pdf",
        AsyncMock(return_value=valid_pdf),
    )
    result = (await downloader.download_targets([target]))[target.target_id]

    assert result is not None
    assert result.was_reused is False
    assert result.file_path.read_bytes() == valid_pdf
    assert not result.file_path.with_suffix(".pdf.part").exists()


@pytest.mark.anyio
async def test_interrupted_part_file_is_never_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = build_target()
    record = build_record()
    valid_pdf = build_pdf_bytes("Dipirona 500 mg comprimido")
    expected_path = tmp_path / "dipirona-500mg-tablet__111__patient.pdf"
    expected_path.with_suffix(".pdf.part").write_bytes(b"interrupted")
    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[record])
    download_mock = AsyncMock(return_value=valid_pdf)
    monkeypatch.setattr(download_bulas, "browser_pdf", download_mock)

    result = (await downloader.download_targets([target]))[target.target_id]

    assert result is not None
    assert result.was_reused is False
    assert expected_path.read_bytes() == valid_pdf
    assert not expected_path.with_suffix(".pdf.part").exists()
    download_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_ambiguous_duplicate_api_records_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloader = build_downloader(tmp_path)
    record = build_record()
    downloader.fetch_all_results = AsyncMock(return_value=[record, record])
    download_mock = AsyncMock()
    monkeypatch.setattr(download_bulas, "browser_pdf", download_mock)

    result = (await downloader.download_targets([build_target()]))[
        "dipirona-500mg-tablet"
    ]

    assert result is None
    download_mock.assert_not_awaited()


@pytest.mark.anyio
async def test_download_is_rejected_when_pdf_identity_terms_do_not_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = build_target()
    downloader = build_downloader(tmp_path)
    downloader.fetch_all_results = AsyncMock(return_value=[build_record()])
    monkeypatch.setattr(
        download_bulas,
        "browser_pdf",
        AsyncMock(return_value=build_pdf_bytes("Outro medicamento 10 mg capsula")),
    )

    result = (await downloader.download_targets([target]))[target.target_id]
    expected_path = tmp_path / "dipirona-500mg-tablet__111__patient.pdf"

    assert result is None
    assert not expected_path.exists()
    assert not expected_path.with_suffix(".pdf.part").exists()


def test_manifest_rejects_duplicate_filename_and_source_identity() -> None:
    content = build_pdf_bytes("Dipirona")
    base_values = {
        "target_id": "target-one",
        "active_ingredient": "dipirona",
        "product_name": "DIPIRONA",
        "strength": "500 mg",
        "pharmaceutical_form": "comprimido",
        "presentation": "caixa com 10 comprimidos",
        "audience": "patient",
        "manufacturer": "EMS S/A",
        "company_tax_id": "00000000000100",
        "anvisa_product_id": 10,
        "registration_number": "123",
        "process_number": "456",
        "expedition_number": "789",
        "transaction_number": "1011",
        "source_record_id": "111",
        "canonical_source_url": "https://consultas.anvisa.gov.br/api/consulta/bulario",
        "source_published_at": "2026-08-20T10:00:00-03:00",
        "search_query": "Dipirona",
        "downloader_version": "2.0",
        "filename": "same.pdf",
        "sha256_checksum": hashlib.sha256(content).hexdigest(),
        "content_size_bytes": len(content),
    }
    first = SystemBulaManifestEntry(**base_values)
    second = SystemBulaManifestEntry(
        **{
            **base_values,
            "target_id": "target-two",
            "source_record_id": "222",
        }
    )

    with pytest.raises(ValidationError, match="duplicate PDF filenames"):
        SystemBulaManifest(documents=[first, second])

    conflicting_source = SystemBulaManifestEntry(
        **{
            **base_values,
            "target_id": "target-three",
            "filename": "different.pdf",
        }
    )
    with pytest.raises(ValidationError, match="duplicate source identities"):
        SystemBulaManifest(documents=[first, conflicting_source])


def test_invalid_protected_document_id_is_rejected() -> None:
    with pytest.raises(AnvisaSelectionError, match="invalid protected document ID"):
        decode_source_record_id("not-a-jwt")


def test_parse_arguments_uses_explicit_target_configuration() -> None:
    arguments = parse_arguments(
        [
            "--output",
            "custom-output",
            "--targets",
            "custom-targets.json",
            "--limit",
            "3",
        ]
    )

    assert arguments.output_directory == Path("custom-output")
    assert arguments.manifest_path == Path("custom-output/manifest.json")
    assert arguments.targets_path == Path("custom-targets.json")
    assert arguments.limit == 3
