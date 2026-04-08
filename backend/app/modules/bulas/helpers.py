from typing import BinaryIO
from pypdf import PdfReader
from pypdf.errors import PdfReadError

class InvalidPdfError(Exception):
    """Raised when the uploaded file cannot be parsed as a valid PDF."""

class PdfTextExtractor:
    
    def extract(self, file: BinaryIO) -> tuple[str, int]:
        """
        Reads a PDF file and returns the concatenated text and the total number of pages.
        """
        try:
            reader = PdfReader(file)
        except PdfReadError as exc:
            raise InvalidPdfError("Arquivo PDF invalido ou corrompido.") from exc

        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        return text, len(reader.pages)

class Chunking:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
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