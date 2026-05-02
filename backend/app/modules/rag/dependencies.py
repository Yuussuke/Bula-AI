from app.modules.rag.parsers.pdf_parser import BulaParser


def get_parser() -> BulaParser:
    return BulaParser(ocr_enabled=False)
