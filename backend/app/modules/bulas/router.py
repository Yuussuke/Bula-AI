from typing import cast

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.modules.auth import models as auth_models
from app.modules.auth.dependencies import get_current_user
from app.modules.bulas.dependencies import get_bula_service
from app.modules.bulas.schemas import BulaResponse
from app.modules.bulas.service import BulaService

router = APIRouter(prefix="/bulas", tags=["bulas"])


@router.post(
    "/upload",
    response_model=BulaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    drug_name: str | None = Form(default=None),
    manufacturer: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
) -> BulaResponse:
    bula = await bula_service.upload_bula(
        user_id=cast(int, current_user.id),
        drug_name=drug_name,
        manufacturer=manufacturer,
        file=file,
    )
    return BulaResponse.model_validate(bula)


@router.get("/", response_model=list[BulaResponse])
async def list_bulas(
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
) -> list[BulaResponse]:
    bulas = await bula_service.list_bulas_for_user(
        user_id=cast(int, current_user.id),
    )
    return [BulaResponse.model_validate(bula) for bula in bulas]
