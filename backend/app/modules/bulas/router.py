from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.modules.auth import models as auth_models
from app.modules.auth.dependencies import get_current_user
from app.modules.bulas.dependencies import get_bula_service
from app.modules.bulas.schemas import (
    BulaResponse,
    BulaStatusResponse,
    SystemBulaResponse,
)
from app.modules.bulas.service import BulaService

router = APIRouter(prefix="/bulas", tags=["bulas"])


@router.post(
    "/upload",
    response_model=BulaResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_file(
    drug_name: str | None = Form(default=None),
    manufacturer: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
) -> BulaResponse:
    bula = await bula_service.upload_and_enqueue_bula(
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


@router.get("/system", response_model=list[SystemBulaResponse])
async def list_system_bulas(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
) -> list[SystemBulaResponse]:
    _ = current_user
    bulas = await bula_service.list_published_system_bulas(
        limit=limit,
        offset=offset,
    )
    return [SystemBulaResponse.from_bula(bula) for bula in bulas]


@router.get("/system/{bula_id}", response_model=SystemBulaResponse)
async def get_system_bula(
    bula_id: UUID,
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
) -> SystemBulaResponse:
    _ = current_user
    bula = await bula_service.get_published_system_bula(bula_id=bula_id)
    return SystemBulaResponse.from_bula(bula)


@router.get("/{bula_id}/status", response_model=BulaStatusResponse)
async def get_bula_status(
    bula_id: UUID,
    current_user: auth_models.User = Depends(get_current_user),
    bula_service: BulaService = Depends(get_bula_service),
) -> BulaStatusResponse:
    bula = await bula_service.get_bula_status_for_user(
        bula_id=bula_id,
        user_id=cast(int, current_user.id),
    )
    return BulaStatusResponse.model_validate(bula)
