import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.bulas.schemas import SystemBulaManifest, SystemBulaManifestEntry
from app.scripts.seed_system_bulas import (
    SeedArguments,
    load_seed_candidates,
    parse_arguments,
)


def test_load_seed_candidates_reads_manifest_pdf_content(tmp_path: Path) -> None:
    pdf_content = b"%PDF-1.4\nleaflet\n%%EOF"
    pdf_path = tmp_path / "dipirona.pdf"
    pdf_path.write_bytes(pdf_content)
    manifest_path = tmp_path / "manifest.json"
    manifest = SystemBulaManifest(
        documents=[
            SystemBulaManifestEntry(
                drug_name="Dipirona",
                manufacturer="Example Pharma",
                source_url="https://consultas.anvisa.gov.br/dipirona.pdf",
                filename=pdf_path.name,
                sha256_checksum=hashlib.sha256(pdf_content).hexdigest(),
                content_size_bytes=len(pdf_content),
            )
        ]
    )
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")
    arguments = SeedArguments(
        input_directory=tmp_path,
        manifest_path=manifest_path,
        admin_email="admin@example.com",
        is_dry_run=True,
        limit=None,
    )

    candidates = load_seed_candidates(arguments)

    assert len(candidates) == 1
    assert candidates[0].content == pdf_content
    assert candidates[0].manifest_entry.drug_name == "Dipirona"


@pytest.mark.parametrize("filename", ["../dipirona.pdf", "..\\dipirona.pdf"])
def test_manifest_rejects_filename_with_directory_component(filename: str) -> None:
    with pytest.raises(ValidationError, match="local PDF filename"):
        SystemBulaManifestEntry(
            drug_name="Dipirona",
            source_url="https://consultas.anvisa.gov.br/dipirona.pdf",
            filename=filename,
            sha256_checksum="0" * 64,
            content_size_bytes=100,
        )


def test_parse_arguments_defaults_to_downloader_output() -> None:
    arguments = parse_arguments(["--admin-email", "admin@example.com", "--dry-run"])

    assert arguments.input_directory == Path("tmp/anvisa-bulas")
    assert arguments.manifest_path == Path("tmp/anvisa-bulas/manifest.json")
    assert arguments.is_dry_run is True
