from dataclasses import dataclass
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidPdfError(Exception):
    """Raised when the uploaded file cannot be parsed as a valid PDF."""


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
        except PdfReadError as exc:
            raise InvalidPdfError("Arquivo PDF invalido ou corrompido.") from exc
        text_pieces: list[str] = []
        for page in reader.pages:
            text_pieces.append(page.extract_text() or "")
        final_text = "".join(text_pieces)
        return ExtractedBula(text=final_text, pages=len(reader.pages))


class Chunking:
    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer.")

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
