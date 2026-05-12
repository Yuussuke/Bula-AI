from __future__ import annotations

import fitz
import pytest

from app.modules.rag.dependencies import get_parser
from app.modules.rag.parsers.handlers import (
    ExtractedLine,
    ExtractedPage,
    ExtractionResult,
    ParserHandler,
    PdfplumberHandler,
)
from app.modules.rag.parsers.markdown_renderer import MarkdownRenderer
from app.modules.rag.parsers.metadata_extractor import MetadataExtractor
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.parsers.section_detector import (
    DetectedSection,
    SectionDetector,
)


class StaticHandler(ParserHandler):
    def __init__(self, extraction_result: ExtractionResult) -> None:
        super().__init__()
        self.extraction_tier = extraction_result.extraction_tier
        self.extraction_result = extraction_result
        self.was_called = False

    def _extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        _ = pdf_bytes
        _ = filename
        self.was_called = True
        return self.extraction_result


def build_extraction_result(
    *,
    text: str,
    extraction_tier: str,
    is_sparse: bool,
    error: str | None = None,
) -> ExtractionResult:
    lines = [
        ExtractedLine(text=line, page_number=1)
        for line in text.splitlines()
        if line.strip()
    ]
    return ExtractionResult(
        text=text,
        extraction_tier=extraction_tier,
        pages=[
            ExtractedPage(
                page_number=1,
                text=text,
                lines=lines,
            )
        ],
        quality_signals={
            "is_sparse": is_sparse,
            "character_count": len(text.strip()),
            "matched_section_keywords": ["COMPOSICAO"] if not is_sparse else [],
        },
        error=error,
    )


def build_text_pdf(lines: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page()
    y_position = 72

    for line in lines:
        page.insert_text((72, y_position), line, fontsize=12)
        y_position += 18

    pdf_bytes = document.tobytes()
    document.close()
    return bytes(pdf_bytes)


def test_sparse_detection_rejects_short_text() -> None:
    handler = PdfplumberHandler()

    is_sparse = handler._is_sparse("COMPOSICAO")

    assert is_sparse is True


def test_sparse_detection_rejects_text_without_anvisa_keywords() -> None:
    handler = PdfplumberHandler()
    text_without_keywords = "Este texto tem tamanho suficiente, mas nao contem secoes. "
    text_without_keywords += "Ele deve ser rejeitado como uma extracao fraca. " * 3

    is_sparse = handler._is_sparse(text_without_keywords)

    assert is_sparse is True


def test_sparse_detection_accepts_text_with_anvisa_keyword() -> None:
    handler = PdfplumberHandler()
    useful_text = "COMPOSICAO\n"
    useful_text += "Cada comprimido contem substancia ativa suficiente. " * 4

    is_sparse = handler._is_sparse(useful_text)

    assert is_sparse is False


def test_handler_chain_keeps_first_successful_extraction() -> None:
    pdfplumber_result = build_extraction_result(
        text="COMPOSICAO\nTexto util para a bula. " * 5,
        extraction_tier="pdfplumber",
        is_sparse=False,
    )
    pymupdf_result = build_extraction_result(
        text="COMPOSICAO\nTexto de fallback. " * 5,
        extraction_tier="pymupdf",
        is_sparse=False,
    )
    pdfplumber_handler = StaticHandler(pdfplumber_result)
    pymupdf_handler = StaticHandler(pymupdf_result)
    pdfplumber_handler.set_next(pymupdf_handler)

    result = pdfplumber_handler.handle(pdf_bytes=b"%PDF-1.4", filename="bula.pdf")

    assert result.extraction_tier == "pdfplumber"
    assert pdfplumber_handler.was_called is True
    assert pymupdf_handler.was_called is False


def test_handler_chain_delegates_sparse_extraction_to_next_handler() -> None:
    sparse_result = build_extraction_result(
        text="pouco texto",
        extraction_tier="pdfplumber",
        is_sparse=True,
    )
    fallback_result = build_extraction_result(
        text="COMPOSICAO\nTexto util extraido pelo fallback. " * 5,
        extraction_tier="pymupdf",
        is_sparse=False,
    )
    pdfplumber_handler = StaticHandler(sparse_result)
    pymupdf_handler = StaticHandler(fallback_result)
    pdfplumber_handler.set_next(pymupdf_handler)

    result = pdfplumber_handler.handle(pdf_bytes=b"%PDF-1.4", filename="bula.pdf")

    assert result.extraction_tier == "pymupdf"
    assert pdfplumber_handler.was_called is True
    assert pymupdf_handler.was_called is True
    assert result.quality_signals["delegated_from"] == [
        {
            "extraction_tier": "pdfplumber",
            "error": None,
            "is_sparse": True,
            "character_count": len("pouco texto"),
        }
    ]


@pytest.mark.anyio
async def test_parser_returns_failure_when_all_tiers_are_sparse() -> None:
    sparse_result = build_extraction_result(
        text="pouco texto",
        extraction_tier="pymupdf",
        is_sparse=True,
    )
    parser = BulaParser(first_handler=StaticHandler(sparse_result))

    result = await parser.parse(pdf_bytes=b"%PDF-1.4", filename="bula.pdf")

    assert result.success is False
    assert result.markdown == ""
    assert result.sections == []
    assert result.error is not None
    assert "OCR is not enabled" in result.error


@pytest.mark.anyio
async def test_parser_converts_text_pdf_to_structured_markdown() -> None:
    pdf_bytes = build_text_pdf(
        [
            "IDENTIFICACAO DO MEDICAMENTO",
            "DIPIRONA SODICA",
            "Registrado por: Exemplo Farmaceutica S.A.",
            "COMPOSICAO",
            "Cada comprimido contem dipirona sodica monoidratada.",
            "INDICACOES",
            "Este medicamento e indicado para dor e febre.",
            "POSOLOGIA E MODO DE USAR",
            "Use conforme orientacao da bula e do profissional de saude.",
        ]
    )
    parser = BulaParser()

    result = await parser.parse(pdf_bytes=pdf_bytes, filename="dipirona.pdf")

    assert result.success is True
    assert result.markdown
    assert result.extraction_tier == "pdfplumber"
    assert "## IDENTIFICACAO DO MEDICAMENTO" in result.markdown
    assert "## COMPOSICAO" in result.markdown
    assert "## POSOLOGIA E MODO DE USAR" in result.markdown
    assert result.sections == [
        "IDENTIFICACAO DO MEDICAMENTO",
        "COMPOSICAO",
        "INDICACOES",
        "POSOLOGIA E MODO DE USAR",
    ]
    assert result.metadata["drug_name"] == "DIPIRONA SODICA"
    assert result.metadata["manufacturer"] == "Exemplo Farmaceutica S.A."
    assert result.metadata["sections_present"] == result.sections
    assert isinstance(result.metadata["section_metadata"], list)


def test_get_parser_returns_bula_parser() -> None:
    parser = get_parser()

    assert isinstance(parser, BulaParser)


def test_section_detector_detects_standard_numbered_and_visual_sections() -> None:
    lines = [
        ExtractedLine(text="COMPOSICAO", page_number=1, average_font_size=12),
        ExtractedLine(
            text="1. Como devo usar este medicamento?",
            page_number=1,
            average_font_size=12,
        ),
        ExtractedLine(
            text="CUIDADOS IMPORTANTES",
            page_number=2,
            average_font_size=16,
            max_font_size=16,
        ),
        ExtractedLine(text="Texto comum da bula.", page_number=2, average_font_size=12),
    ]
    detector = SectionDetector()

    detected_sections = detector.detect(lines)

    assert [section.title for section in detected_sections] == [
        "COMPOSICAO",
        "Como devo usar este medicamento?",
        "CUIDADOS IMPORTANTES",
    ]
    assert [section.level for section in detected_sections] == [2, 2, 3]
    assert [section.line_index for section in detected_sections] == [0, 1, 2]


def test_section_detector_merges_wrapped_visual_heading_sections() -> None:
    lines = [
        ExtractedLine(
            text="O QUE DEVO SABER ANTES DE USAR",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
        ExtractedLine(
            text="ESTE MEDICAMENTO",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
        ExtractedLine(
            text="Informe ao medico se estiver usando outros medicamentos.",
            page_number=1,
            average_font_size=12,
        ),
    ]
    detector = SectionDetector()

    detected_sections = detector.detect(lines)

    assert len(detected_sections) == 1
    assert (
        detected_sections[0].title == "O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO"
    )
    assert detected_sections[0].line_index == 0
    assert detected_sections[0].consumed_line_indices == (0, 1)


def test_section_detector_merges_heading_wrapped_across_three_lines() -> None:
    lines = [
        ExtractedLine(
            text="O QUE DEVO SABER ANTES",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
        ExtractedLine(
            text="DE USAR ESTE",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
        ExtractedLine(
            text="MEDICAMENTO",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
        ExtractedLine(
            text="Informe ao medico se estiver usando outros medicamentos.",
            page_number=1,
            average_font_size=12,
        ),
    ]
    detector = SectionDetector()

    detected_sections = detector.detect(lines)

    assert len(detected_sections) == 1
    assert (
        detected_sections[0].title == "O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO"
    )
    assert detected_sections[0].consumed_line_indices == (0, 1, 2)


def test_section_detector_does_not_merge_wrapped_heading_after_question_mark() -> None:
    lines = [
        ExtractedLine(
            text="QUEM DEVE AVALIAR ESTE RISCO?",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
        ExtractedLine(
            text="ANTES DO USO",
            page_number=1,
            average_font_size=12,
            is_bold=True,
        ),
    ]
    detector = SectionDetector()

    detected_sections = detector.detect(lines)

    assert [section.title for section in detected_sections] == [
        "QUEM DEVE AVALIAR ESTE RISCO?",
        "ANTES DO USO",
    ]


def test_markdown_renderer_builds_headings_and_section_offsets() -> None:
    lines = [
        ExtractedLine(text="COMPOSICAO", page_number=1),
        ExtractedLine(text="Cada comprimido contem dipirona.", page_number=1),
        ExtractedLine(text="INDICACOES", page_number=2),
        ExtractedLine(text="Este medicamento e indicado para dor.", page_number=2),
    ]
    detected_sections = [
        DetectedSection(
            title="COMPOSICAO",
            canonical_title="Composicao",
            level=2,
            page_number=1,
            line_index=0,
        ),
        DetectedSection(
            title="INDICACOES",
            canonical_title="Indicacoes",
            level=2,
            page_number=2,
            line_index=2,
        ),
    ]
    renderer = MarkdownRenderer()

    result = renderer.render(lines=lines, detected_sections=detected_sections)

    assert result.markdown == (
        "## COMPOSICAO\n"
        "Cada comprimido contem dipirona.\n"
        "\n"
        "## INDICACOES\n"
        "Este medicamento e indicado para dor."
    )
    assert result.sections == ["COMPOSICAO", "INDICACOES"]
    assert result.detected_sections[0].char_start == 0
    assert (
        result.detected_sections[0].char_end == result.detected_sections[1].char_start
    )
    assert result.detected_sections[1].char_end == len(result.markdown)


def test_markdown_renderer_skips_wrapped_heading_continuation_lines() -> None:
    lines = [
        ExtractedLine(text="O QUE DEVO SABER ANTES DE USAR", page_number=1),
        ExtractedLine(text="ESTE MEDICAMENTO", page_number=1),
        ExtractedLine(
            text="Informe ao medico se estiver usando outro remedio.", page_number=1
        ),
    ]
    detected_sections = [
        DetectedSection(
            title="O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO",
            canonical_title="O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO",
            level=3,
            page_number=1,
            line_index=0,
            consumed_line_indices=(0, 1),
        )
    ]
    renderer = MarkdownRenderer()

    result = renderer.render(lines=lines, detected_sections=detected_sections)

    assert result.markdown == (
        "### O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO\n"
        "Informe ao medico se estiver usando outro remedio."
    )
    assert result.markdown.count("###") == 1
    assert "\nESTE MEDICAMENTO\n" not in result.markdown


def test_markdown_renderer_skips_repeated_section_headings() -> None:
    lines = [
        ExtractedLine(text="COMPOSICAO", page_number=1),
        ExtractedLine(text="Texto da primeira composicao.", page_number=1),
        ExtractedLine(text="COMPOSICAO", page_number=2),
        ExtractedLine(text="Texto depois da repeticao.", page_number=2),
    ]
    detected_sections = [
        DetectedSection(
            title="COMPOSICAO",
            canonical_title="Composicao",
            level=2,
            page_number=1,
            line_index=0,
        ),
        DetectedSection(
            title="COMPOSICAO",
            canonical_title="Composicao",
            level=2,
            page_number=2,
            line_index=2,
        ),
    ]
    renderer = MarkdownRenderer()

    result = renderer.render(lines=lines, detected_sections=detected_sections)

    assert result.sections == ["COMPOSICAO"]
    assert "## COMPOSICAO\nTexto da primeira composicao." in result.markdown
    assert "Texto depois da repeticao." in result.markdown
    assert result.markdown.count("## COMPOSICAO") == 1


def test_metadata_extractor_keeps_existing_metadata_shape() -> None:
    lines = [
        ExtractedLine(text="DIPIRONA SODICA", page_number=1),
        ExtractedLine(text="Registrado por: Exemplo Farmaceutica S.A.", page_number=1),
    ]
    detected_sections = [
        DetectedSection(
            title="COMPOSICAO",
            canonical_title="Composicao",
            level=2,
            page_number=1,
            line_index=2,
            char_start=0,
            char_end=42,
        )
    ]
    quality_signals = {
        "is_sparse": False,
        "character_count": 120,
        "matched_section_keywords": ["COMPOSICAO"],
    }
    extractor = MetadataExtractor()

    metadata = extractor.extract(
        lines=lines,
        filename="dipirona.pdf",
        markdown_sections=["COMPOSICAO"],
        detected_sections=detected_sections,
        quality_signals=quality_signals,
    )

    assert metadata == {
        "drug_name": "DIPIRONA SODICA",
        "drug_name_source": "text",
        "manufacturer": "Exemplo Farmaceutica S.A.",
        "sections_present": ["COMPOSICAO"],
        "section_metadata": [
            {
                "title": "COMPOSICAO",
                "canonical_title": "Composicao",
                "level": 2,
                "page_number": 1,
                "char_start": 0,
                "char_end": 42,
            }
        ],
        "quality_signals": quality_signals,
    }


def test_metadata_extractor_uses_filename_as_low_priority_drug_name() -> None:
    lines = [
        ExtractedLine(text="BULA PARA O PACIENTE", page_number=1),
        ExtractedLine(text="COMPOSICAO", page_number=1),
    ]
    extractor = MetadataExtractor()

    metadata = extractor.extract(
        lines=lines,
        filename="bula_dipirona_sodica.pdf",
        markdown_sections=[],
        detected_sections=[],
        quality_signals={},
    )

    assert metadata["drug_name"] == "bula dipirona sodica"
    assert metadata["drug_name_source"] == "filename_best_effort"
    assert metadata["manufacturer"] is None
