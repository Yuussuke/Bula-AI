from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status

from app.modules.auth import models as auth_models
from app.modules.auth.dependencies import get_current_user
from app.modules.bulas.schemas import BulaUploadResponse
from app.modules.bulas.service import BulaService
from app.modules.bulas.helpers import InvalidPdfError
from app.modules.bulas.dependencies import get_bula_service

router = APIRouter(prefix="/bulas", tags=["bulas"])

@router.post(
    "/upload", 
    response_model=BulaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    drug_name: str = Form(...),
    manufacturer: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
):
    try:
        result = await bula_service.process_pdf(
            user_id=current_user.id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file=file.file,
            filename=file.filename,
        )
    except InvalidPdfError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return result