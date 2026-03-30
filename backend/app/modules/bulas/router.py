from fastapi import APIRouter, UploadFile, File

from app.modules.bulas.service import process_bula_pdf

router = APIRouter(prefix="", tags=["bulas"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    result = process_bula_pdf(file.file, filename=file.filename)
    return result