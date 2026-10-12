"""Exercise real conversion, geometric repair and Markdown assembly offline."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pymupdf
import pymupdf4llm
import pytest

from app.modules.rag.parsers.geometric_tables import GeometricTableIntegrator
from app.modules.rag.parsers.pdf_parser import BulaParser, PARSER_VERSION


@pytest.mark.anyio
@pytest.mark.parametrize("page_rotation", [0, 90, 180, 270])
async def test_parser_normalizes_only_the_in_memory_pdf(page_rotation: int) -> None:
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (40, 40), "COMPOSIÇÃO\nExample product\nInstructions for patients."
        )
        for x_position in (40, 180, 320):
            page.draw_rect(
                (x_position, 80, x_position + 0.5, 220), color=None, fill=(0, 0, 0)
            )
        for y_position in (80, 150, 220):
            page.draw_rect(
                (40, y_position, 320, y_position + 0.5), color=None, fill=(0, 0, 0)
            )
        for row in range(2):
            for column in range(2):
                value = (
                    ("Population", "Instruction"),
                    ("Adults", "Read instructions"),
                )[row][column]
                page.insert_text((45 + column * 140, 110 + row * 70), value)
        page.insert_textbox(
            (40, 260, 530, 500), "Preserve the rest of the document. " * 30
        )
        # The visible layout stays upright while /Rotate metadata varies.
        with pymupdf.open() as encoded:
            size = (
                (page.rect.height, page.rect.width)
                if page_rotation in (90, 270)
                else (page.rect.width, page.rect.height)
            )
            rotated = encoded.new_page(width=size[0], height=size[1])
            rotated.show_pdf_page(rotated.rect, document, 0, rotate=page_rotation)
            rotated.set_rotation(page_rotation)
            source = encoded.tobytes()
    checksum = hashlib.sha256(source).hexdigest()
    parsed = await BulaParser().parse(source, "synthetic-layout.pdf")
    assert parsed.success, parsed.error
    assert parsed.parser_version == PARSER_VERSION
    assert "Adults" in parsed.markdown
    assert "Read instructions" in parsed.markdown
    assert "Preserve the rest" in parsed.markdown
    assert parsed.cleanup_summary is not None
    assert parsed.cleanup_summary["table_extraction"]["geometric_table_count"] == 1
    assert hashlib.sha256(source).hexdigest() == checksum
    with pymupdf.open(stream=source, filetype="pdf") as unchanged:
        assert unchanged[0].rotation == page_rotation


REGRESSION_PDFS = [
    (
        "A-B007",
        "final/B007/bula_1791246736061.pdf",
        "b06c6761037ce03395a19d6e686baed64efa4bbce5cdbbb8bf65850072227c2c",
    ),
    (
        "A-B018",
        "final/B018/bula_1791246890013.pdf",
        "13e524b83eab65964b7852d1e096894d79a8a02d27eadf30d80472c01fbd93d3",
    ),
    (
        "A-B038",
        "final/B038/bula_1791247291427.pdf",
        "6af0132b12d269b8997c6085e335fbe0a183d8f0acd32d8d6076806db4001456",
    ),
    (
        "A-B049",
        "final/B049/bula_1791247433429.pdf",
        "7c120618bebaaebdebb15fb19824ba29463fa6e649d5021b8a7e5d4b0d574131",
    ),
    (
        "B-CB002",
        "corpus-b/CB002/bula_1791329439872.pdf",
        "688791db3755ee3c12a59081f885bd9fd2544960600de19b18e565647c205986",
    ),
    (
        "B-CB006",
        "corpus-b/CB006/bula_1791329451238.pdf",
        "e5fa58695e3c7aa939467bbfca43ce46d02d8552be12369bd9f7d034355fad0f",
    ),
    (
        "B-CB024",
        "corpus-b/CB024/bula_1791329613221.pdf",
        "66c541f306b4737a2839eb56a25943fc44ce5b50fea1b86dd2c0412297742076",
    ),
]


@pytest.mark.anyio
@pytest.mark.parametrize(("identity", "relative_path", "checksum"), REGRESSION_PDFS)
async def test_local_leaflet_preserves_repaired_relationships(
    identity: str, relative_path: str, checksum: str
) -> None:
    corpus_root = os.environ.get("PARSER_CORPUS_PDFS")
    if corpus_root is None:
        pytest.skip(
            "Original external PDFs are optional; synthetic layout tests run in CI."
        )
    pdf_path = Path(corpus_root) / relative_path
    source = pdf_path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == checksum
    parsed = await BulaParser().parse(source, pdf_path.name)
    if identity == "A-B038":
        assert parsed.success, parsed.error
        assert parsed.cleanup_summary is not None
        tables = parsed.cleanup_summary["table_extraction"]["tables"]
        continued = next(table for table in tables if table["page"] == 3)
        assert continued["columns"] == 14
        assert continued["continuation_of"] == "p2:t0"
        assert continued["continuation_method"] == "relative_schema_and_anchors"
        assert all(cell["page"] == 3 for cell in continued["cells"])
        assert all(cell["page"] == 2 for cell in continued["header_source_cells"])
        composition = parsed.markdown.split("## COMPOSIÇÃO", maxsplit=1)[1].split(
            "INFORMAÇÕES AO PACIENTE", maxsplit=1
        )[0]
        table_rows = [line for line in composition.splitlines() if line.startswith("|")]
        assert (
            len(table_rows) == 17
        )  # Two header tiers, one separator, 14 physical data rows.
        assert sum("---" in line for line in table_rows) == 1
        assert all(len(line.split("|")) == 16 for line in table_rows)
        first_continued = [
            value.strip() for value in table_rows[6].strip("|").split("|")
        ]
        assert first_continued[1:] == [
            "1,5",
            "538",
            "448",
            "18,3",
            "5,08",
            "344",
            "5,2",
            "132",
            "2,5",
            "0,5",
            "95",
            "40",
            "2000",
        ]
        # Independently transcribed from the physical composition table, not
        # from retrieval outputs. These six formulations cover all 14 data rows.
        formulations = [
            ("1,5", "25,7", "346", "3,5", "96", ["2500", "5000", "6000"]),
            ("1,5", "18,3", "344", "2,5", "95", ["2000", "6000"]),
            ("2,5", "25,7", "396", "3,5", "96", ["2500", "6000"]),
            ("2,5", "18,3", "395", "2,5", "95", ["2000", "6000"]),
            ("4,25", "25,7", "485", "3,5", "96", ["2500", "5000", "6000"]),
            ("4,25", "18,3", "483", "2,5", "95", ["2000", "6000"]),
        ]
        expected_numbers = [
            [
                glucose,
                "538",
                "448",
                calcium_mass,
                "5,08",
                osmolarity,
                "5,2",
                "132",
                ionic_calcium,
                "0,5",
                chloride,
                "40",
                volume,
            ]
            for glucose, calcium_mass, osmolarity, ionic_calcium, chloride, volumes in formulations
            for volume in volumes
        ]
        actual_numbers = [
            [value.strip() for value in line.strip("|").split("|")][1:]
            for line in table_rows[3:]
        ]
        assert actual_numbers == expected_numbers
        header_cells = continued["header_source_cells"]
        assert any(
            cell["column_start"] == 1 and cell["text"] == "glicose monoidratada (g)"
            for cell in header_cells
        )
        assert any(
            cell["column_start"] == 9 and cell["text"] == "cálcio"
            for cell in header_cells
        )
        assert any(
            cell["column_start"] == 8
            and cell["column_end"] == 13
            and "mEq/L" in cell["text"]
            for cell in header_cells
        )
        assert any(
            cell["column_start"] == 13 and "(mL)" in cell["text"]
            for cell in header_cells
        )
        origin = next(table for table in tables if table["page"] == 2)
        assert any(
            cell["column_start"] == 4
            and "(mg)" in cell["text"]
            and cell["text_direction"] == [0, -1]
            for cell in origin["cells"]
        )
        with pymupdf.open(stream=source, filetype="pdf") as document:
            for page in document:
                if page.rotation:
                    page.remove_rotation()
            chunks = pymupdf4llm.to_markdown(
                document,
                pages=[15],
                page_chunks=True,
                use_ocr=False,
                force_ocr=False,
                show_progress=False,
            )
            summary = GeometricTableIntegrator().repair(document, chunks)
            assert summary["geometric_table_count"] > 0
            assert "glicose monoidratada (g)" in chunks[0]["text"]
            assert "Concentração Iônica" in chunks[0]["text"]
        assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == checksum
        return
    assert parsed.success, parsed.error
    assert parsed.metadata["parser_version"] == PARSER_VERSION
    if identity == "A-B018":
        expected_pairs = [
            ("1. Retirar o comprimido", "2. Colocar o comprimido"),
            ("3. Aguardar alguns minutos", "4.Dar imediatamente"),
            ("5. Se observar partículas", "6. Administre inteiramente"),
        ]
        for first, second in expected_pairs:
            matching_rows = [
                line for line in parsed.markdown.splitlines() if first in line
            ]
            assert len(matching_rows) == 1
            assert second in matching_rows[0]
        assert "7. Registre a administração" in parsed.markdown
    elif identity == "B-CB024":
        matching_rows = [
            line
            for line in parsed.markdown.splitlines()
            if "Meningite asséptica" in line
        ]
        assert len(matching_rows) == 1
        assert "| Neurológico |" in matching_rows[0]
        assert "<0,01%" in matching_rows[0]
    elif identity == "B-CB006":
        matching_rows = [
            line for line in parsed.markdown.splitlines() if "0667735/25-9" in line
        ]
        assert len(matching_rows) == 1
        assert "16/05/2025" in matching_rows[0]
        assert "VP07" in matching_rows[0]
    elif identity == "A-B049":
        assert "Terapia contínua" in parsed.markdown
        assert "Terapia cíclica" in parsed.markdown
        assert "Semana" in parsed.markdown
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == checksum
