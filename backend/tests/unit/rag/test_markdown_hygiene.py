from app.modules.rag.parsers.handlers import ExtractedLine
from app.modules.rag.parsers.markdown_hygiene import trim_lines_from_last_legal_section


def test_mentions_in_prose_and_tables_do_not_replace_last_heading() -> None:
    lines = [
        ExtractedLine(text="COMPOSICAO", page_number=1),
        ExtractedLine(text="Primeira apresentacao.", page_number=1),
        ExtractedLine(text="DIZERES LEGAIS", page_number=1),
        ExtractedLine(text="Segunda apresentacao: uso adulto.", page_number=2),
        ExtractedLine(text="### III - DIZERES LEGAIS", page_number=2),
        ExtractedLine(text="Historico de alteracao.", page_number=3),
        ExtractedLine(text="| Alteracao | DIZERES LEGAIS |", page_number=3),
        ExtractedLine(text="Foram alterados os dizeres legais.", page_number=3),
    ]
    preserved, sections = trim_lines_from_last_legal_section(lines, [])
    assert preserved == lines[:4]
    assert sections == []
    assert len(lines) == 8


def test_missing_heading_preserves_all_source_lines() -> None:
    lines = [
        ExtractedLine(text="COMPOSICAO", page_number=1),
        ExtractedLine(text="Consulte os dizeres legais.", page_number=1),
        ExtractedLine(text="| DIZERES LEGAIS | Registro |", page_number=2),
    ]
    preserved, sections = trim_lines_from_last_legal_section(lines, [])
    assert preserved == lines
    assert sections == []
