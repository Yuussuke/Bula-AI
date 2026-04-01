from typing import BinaryIO
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bulas.repository import create_document


def extract_text_from_pdf(file: BinaryIO) -> tuple[str, int]:
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text, len(reader.pages)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


async def process_bula_pdf(
    file: BinaryIO,
    db: AsyncSession,
    filename: str | None = None,
) -> dict:
    text, pages = extract_text_from_pdf(file)
    chunks = chunk_text(text)

    safe_name = filename or "arquivo_sem_nome.pdf"

    try:
        doc = await create_document(db, safe_name)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "filename": safe_name,
        "pages": pages,
        "characters": len(text),
        "chunks": len(chunks),
        "document_id": doc.id,
    }