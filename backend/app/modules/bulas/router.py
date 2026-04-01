# app/modules/bulas/router.py
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bulas.service import process_bula_pdf

router = APIRouter(prefix="/bulas", tags=["bulas"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await process_bula_pdf(file.file, db=db, filename=file.filename)
    return result