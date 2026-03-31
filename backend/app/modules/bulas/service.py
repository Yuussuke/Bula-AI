from pypdf import PdfReader
from app.modules.bulas.repository import create_document
from app.core.db.session import SessionLocal

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text, len(reader.pages)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def process_bula_pdf(file, filename: str | None = None) -> dict:
    text, pages = extract_text_from_pdf(file)
    chunks = chunk_text(text)

    db = SessionLocal()
    doc = create_document(db, filename)
    db.close()

    return {
        "filename": filename,
        "pages": pages,
        "characters": len(text),
        "chunks": len(chunks),
        "document_id": doc.id,
    }