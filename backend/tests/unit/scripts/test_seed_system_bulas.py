from datetime import UTC, datetime
import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.bulas.schemas import (
    SystemBulaManifest,
    SystemBulaManifestEntry,
    SystemBulaManifestReview,
)
from app.scripts.seed_system_bulas import (
    SeedArguments,
    load_seed_candidates,
    parse_arguments,
)
from tests.pdf_factory import build_pdf_bytes


def build_manifest_entry(
    *,
    content: bytes,
    filename: str = "dipirona.pdf",
    is_approved: bool = True,
) -> SystemBulaManifestEntry:
    review = (
        SystemBulaManifestReview(
            status="approved",
            reviewed_by="reviewer@example.com",
            reviewed_at=datetime.now(UTC),
        )
        if is_approved
        else SystemBulaManifestReview()
    )
    return SystemBulaManifestEntry(
        target_id="dipirona-500mg-tablet",
        active_ingredient="dipirona monoidratada",
        product_name="DIPIRONA",
        strength="500 mg",
        pharmaceutical_form="comprimido",
        presentation="caixa com 10 comprimidos",
        audience="patient",
        manufacturer="EMS S/A",
        company_tax_id="00000000000100",
        anvisa_product_id=10,
        registration_number="123456789",
        process_number="process-1",
        expedition_number="987654",
        transaction_number="transaction-1",
        source_record_id="111",
        canonical_source_url=(
            "https://consultas.anvisa.gov.br/api/consulta/bulario"
            "?filter%5BnomeProduto%5D=Dipirona"
        ),
        source_published_at="2026-08-20T10:00:00-03:00",
        source_updated_at="2026-08-21T10:00:00-03:00",
        search_query="Dipirona",
        downloader_version="2.0",
        filename=filename,
        sha256_checksum=hashlib.sha256(content).hexdigest(),
        content_size_bytes=len(content),
        review=review,
    )


def build_arguments(tmp_path: Path) -> SeedArguments:
    return SeedArguments(
        input_directory=tmp_path,
        manifest_path=tmp_path / "manifest.json",
        admin_email="admin@example.com",
        is_dry_run=True,
        limit=None,
    )


def test_load_seed_candidates_reads_human_approved_pdf(tmp_path: Path) -> None:
    pdf_content = build_pdf_bytes("Dipirona 500 mg comprimido")
    pdf_path = tmp_path / "dipirona.pdf"
    pdf_path.write_bytes(pdf_content)
    manifest = SystemBulaManifest(documents=[build_manifest_entry(content=pdf_content)])
    (tmp_path / "manifest.json").write_text(
        manifest.model_dump_json(),
        encoding="utf-8",
    )

    candidates = load_seed_candidates(build_arguments(tmp_path))

    assert len(candidates) == 1
    assert candidates[0].content == pdf_content
    assert candidates[0].manifest_entry.product_name == "DIPIRONA"


def test_load_seed_candidates_rejects_pending_review(tmp_path: Path) -> None:
    pdf_content = build_pdf_bytes("Dipirona 500 mg comprimido")
    (tmp_path / "dipirona.pdf").write_bytes(pdf_content)
    manifest = SystemBulaManifest(
        documents=[build_manifest_entry(content=pdf_content, is_approved=False)]
    )
    (tmp_path / "manifest.json").write_text(
        manifest.model_dump_json(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="human-approved"):
        load_seed_candidates(build_arguments(tmp_path))


@pytest.mark.parametrize("filename", ["../dipirona.pdf", "..\\dipirona.pdf"])
def test_manifest_rejects_filename_with_directory_component(filename: str) -> None:
    pdf_content = build_pdf_bytes()
    with pytest.raises(ValidationError, match="local PDF filename"):
        build_manifest_entry(content=pdf_content, filename=filename)


def test_parse_arguments_defaults_to_downloader_output() -> None:
    arguments = parse_arguments(["--admin-email", "admin@example.com", "--dry-run"])

    assert arguments.input_directory == Path("tmp/anvisa-bulas-v2")
    assert arguments.manifest_path == Path("tmp/anvisa-bulas-v2/manifest.json")
    assert arguments.is_dry_run is True
