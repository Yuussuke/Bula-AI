from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Sequence

from pypdf import PdfReader
from pypdf.errors import PyPdfError


class InvalidPdfError(Exception):
    """Raised when the uploaded file cannot be parsed as a valid PDF."""


PDF_MAGIC_BYTES = b"%PDF-"
PDF_EOF_MARKER = b"%%EOF"


def validate_pdf_bytes(
    content: bytes,
    *,
    max_size_bytes: int,
    expected_text_terms: Sequence[str] = (),
) -> None:
    if len(content) > max_size_bytes:
        raise InvalidPdfError("Arquivo PDF excede o tamanho maximo permitido.")

    if not content.startswith(PDF_MAGIC_BYTES):
        raise InvalidPdfError("Arquivo sem assinatura PDF valida.")

    if PDF_EOF_MARKER not in content[-1_024:]:
        raise InvalidPdfError("Arquivo PDF incompleto: marcador EOF ausente.")

    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if len(reader.pages) == 0:
            raise InvalidPdfError("Arquivo PDF nao possui paginas.")
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (OSError, PyPdfError, ValueError) as exc:
        raise InvalidPdfError("Arquivo PDF invalido ou corrompido.") from exc

    normalized_text = " ".join(extracted_text.casefold().split())
    missing_terms = [
        term
        for term in expected_text_terms
        if " ".join(term.casefold().split()) not in normalized_text
    ]
    if missing_terms:
        joined_terms = ", ".join(missing_terms)
        raise InvalidPdfError(
            f"Identidade esperada nao encontrada no PDF: {joined_terms}."
        )


@dataclass
class ExtractedBula:
    text: str
    pages: int


class PdfTextExtractor:
    def extract(self, file: BinaryIO) -> ExtractedBula:
        """
        Reads a PDF file and returns the concatenated text and the total number of pages.
        """
        try:
            reader = PdfReader(file)
            text_pieces: list[str] = []
            for page in reader.pages:
                text_pieces.append(page.extract_text() or "")
        except PyPdfError as exc:
            raise InvalidPdfError("Arquivo PDF invalido ou corrompido.") from exc

        final_text = "".join(text_pieces)
        return ExtractedBula(text=final_text, pages=len(reader.pages))


class Chunking:
    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if overlap >= chunk_size:
            raise ValueError("Sobreposição deve ser menor que o tamanho do chunk.")
        if chunk_size <= 0:
            raise ValueError("Tamanho do chunk deve ser um inteiro positivo.")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        """Splits a large string into smaller chunks based on the class rules."""
        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.overlap

        return chunks
