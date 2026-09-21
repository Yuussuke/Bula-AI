"""Local real-leaflet regression; downloaded PDFs remain outside version control."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.modules.rag.chunker import BulaChunker
from app.modules.rag.debug_artifacts import RAGIngestionDebugArtifacts
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.schemas import ChunkingConfig


EMS_PATH = Path(__file__).resolve().parents[3] / "tmp/anvisa-bulas/Amoxicilina__EMS.pdf"
EMS_CHECKSUM = "ffd3780e4895c67b9bf1986127e4a205265245f865b6b0123843400582689d41"


@pytest.mark.anyio
async def test_ems_pdf_preserves_table_relationships_through_fallback_and_debug(
    tmp_path: Path,
) -> None:
    if not EMS_PATH.exists():
        pytest.skip(
            "Local ANVISA EMS PDF not downloaded; synthetic geometry tests run in CI."
        )
    source = EMS_PATH.read_bytes()
    assert hashlib.sha256(source).hexdigest() == EMS_CHECKSUM
    parsed = await BulaParser().parse(source, EMS_PATH.name)
    assert parsed.success, parsed.error
    expected_rows = [
        "| Idade | Apresentação | Dosagem |",
        "| Adultos e crianças acima de<br>12 anos* | Comprimidos revestidos 500 mg<br>+ 125 mg | 1 comprimido três vezes ao dia (de<br>8 em 8 horas) |",
        "| Sem alterações de dosagem | 1 comprimido de 500 mg + 125<br>mg de 12 em 12 horas | Os comprimidos de 500mg + 125mg<br>não são recomendados |",
        "| Sem alterações de dosagem | 18,75 mg*/kg duas vezes ao dia<br>(de 12 em 12 horas) (máximo de<br>duas doses de 625 mg ao dia) | 18,75 mg*/kg em dose única diária<br>(máximo de 625 mg) |",
    ]
    for row in expected_rows:
        assert parsed.markdown.count(row) == 1
    assert "### Insuficiência leve Insuficiência moderada" not in parsed.markdown
    assert "Idade Apresentação Dosagem" not in parsed.sections

    # Exercise the actual semantic failure path without contacting a provider.
    llm = AsyncMock()
    llm.chat.completions.create.side_effect = TimeoutError("controlled test timeout")
    config = ChunkingConfig()
    chunks = await BulaChunker(llm=llm, config=config).chunk_markdown(
        parsed.markdown, "ems-test"
    )
    for row in expected_rows[1:]:
        containing = [chunk for chunk in chunks.chunks if row in chunk.text]
        assert len(containing) == 1
        assert containing[0].method == "deterministic"
        assert "| --- | --- | --- |" in containing[0].text
    renal_adults = next(
        chunk for chunk in chunks.chunks if expected_rows[2] in chunk.text
    )
    renal_children = next(
        chunk for chunk in chunks.chunks if expected_rows[3] in chunk.text
    )
    assert "Adultos" in renal_adults.text
    assert "Crianças" in renal_children.text
    assert "*Cada dose de 18,75 mg" in renal_children.text

    debug = RAGIngestionDebugArtifacts(enabled=True, root_path=tmp_path)
    result = await debug.write_run_artifacts(
        run_id="table-regression",
        doc_id="ems-test",
        filename=EMS_PATH.name,
        status="success",
        parse_result=parsed,
        markdown=parsed.markdown,
        chunk_result=chunks,
        chunking_config=config,
    )
    assert result.artifact_write_failures == []
    manifest = json.loads(
        next(tmp_path.rglob("manifest.json")).read_text(encoding="utf-8")
    )
    assert manifest["parser_version"] == "native_markdown_tables_v2"
    tables = manifest["cleanup_summary"]["table_extraction"]["tables"]
    assert [table["columns"] for table in tables if table["page"] == 4] == [3, 3, 3]
    assert "api_key" not in json.dumps(manifest)
