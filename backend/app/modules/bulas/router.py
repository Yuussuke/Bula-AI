from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bulas.schemas import BulaUploadResponse
from app.modules.bulas.service import BulaService
from app.modules.bulas.helpers import PdfTextExtractor, Chunking, InvalidPdfError
from app.modules.bulas.repository import DocumentRepository

router = APIRouter(prefix="/bulas", tags=["bulas"])

@router.post(
    "/upload", 
    response_model=BulaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    extractor = PdfTextExtractor()
    chunker = Chunking()

    service = BulaService(
        document_repo=repo, 
        pdf_extractor=extractor, 
        chunking=chunker
    )

    try:
        result = await service.process_pdf(file=file.file, filename=file.filename)
    except InvalidPdfError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return result