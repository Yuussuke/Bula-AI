import hashlib
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import Page

from app.modules.bulas.schemas import SystemBulaManifest
from scripts.download_bulas import (
    AnvisaBulaDownloader,
    AnvisaBulaRecord,
    matches_manufacturer,
    parse_arguments,
)


@pytest.mark.anyio
async def test_downloader_reuses_valid_pdf_and_writes_manifest(
    tmp_path: Path,
) -> None:
    pdf_content = b"%PDF-1.4\n" + b"leaflet" * 200
    pdf_path = tmp_path / "Dipirona__EMS.pdf"
    pdf_path.write_bytes(pdf_content)
    manifest_path = tmp_path / "manifest.json"
    downloader = AnvisaBulaDownloader(
        page=cast(Page, object()),
        output_directory=tmp_path,
        manifest_path=manifest_path,
    )
    downloader.fetch_all_results = AsyncMock(
        return_value=[
            AnvisaBulaRecord(
                razaoSocial="EMS S/A",
                idBulaPacienteProtegido="patient-document-id",
                dataAtualizacao="2026-08-20",
            )
        ]
    )

    results = await downloader.download_targets([("Dipirona", ["EMS"])])

    result = results["Dipirona"]
    assert result is not None
    assert result.file_path == pdf_path
    assert (
        result.manifest_entry.sha256_checksum == hashlib.sha256(pdf_content).hexdigest()
    )
    manifest = SystemBulaManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    assert len(manifest.documents) == 1
    assert manifest.documents[0].drug_name == "Dipirona"
    assert manifest.documents[0].manufacturer == "EMS S/A"


def test_manufacturer_matching_accepts_known_alias() -> None:
    assert matches_manufacturer("EMS S/A", "EMS") is True
    assert matches_manufacturer("SANOFI MEDLEY FARMACEUTICA LTDA", "Sanofi") is False


def test_parse_arguments_uses_manifest_inside_output_directory() -> None:
    arguments = parse_arguments(["--output", "custom-output", "--limit", "3"])

    assert arguments.output_directory == Path("custom-output")
    assert arguments.manifest_path == Path("custom-output/manifest.json")
    assert arguments.limit == 3
