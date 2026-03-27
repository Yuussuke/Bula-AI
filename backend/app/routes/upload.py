from fastapi import APIRouter, UploadFile, File
from app.services.pdf import extract_text_from_pdf, chunk_text

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    text, pages = extract_text_from_pdf(file.file)

    chunks = chunk_text(text)

    return {
        "filename": file.filename,
        "pages": pages,
        "characters": len(text),
        "chunks": len(chunks)
    }