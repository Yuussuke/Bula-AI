from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Response
from app.core.deps import get_idempotency_key

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.bulas.curation_schemas import (
    CurationDecision,
    CurationListQuery,
    SharedBulaDetail,
    SharedBulaPage,
    SharedSourceInput,
    SharedUploadInput,
    CurationMutationResponse,
    SharedMetadataSuggestion,
)
from app.modules.bulas.curation_service import CurationService
from app.modules.bulas.dependencies import get_curation_service


router = APIRouter(prefix="/bulas/shared", tags=["curation"])


@router.post("", response_model=CurationMutationResponse, status_code=201)
async def submit_shared_bula(
    payload: Annotated[SharedUploadInput, Form(media_type="multipart/form-data")],
    operation_id: UUID = Depends(get_idempotency_key),
    actor: User = Depends(get_current_user),
    service: CurationService = Depends(get_curation_service),
) -> CurationMutationResponse:
    return await service.submit(
        actor=actor,
        file=payload.file,
        source=SharedSourceInput(
            source_url=payload.source_url,
            source_description=payload.source_description,
            product_name=payload.product_name,
            manufacturer=payload.manufacturer,
        ),
        operation_id=operation_id,
    )


@router.get("", response_model=SharedBulaPage)
async def list_shared_bulas(
    filters: Annotated[CurationListQuery, Query()],
    actor: User = Depends(get_current_user),
    service: CurationService = Depends(get_curation_service),
) -> SharedBulaPage:
    return await service.list_page(actor=actor, filters=filters)


@router.get("/{bula_id}", response_model=SharedBulaDetail)
async def get_shared_bula(
    bula_id: UUID,
    actor: User = Depends(get_current_user),
    service: CurationService = Depends(get_curation_service),
) -> SharedBulaDetail:
    return await service.detail(actor=actor, bula_id=bula_id)


@router.get("/{bula_id}/pdf")
async def get_shared_pdf(
    bula_id: UUID,
    actor: User = Depends(get_current_user),
    service: CurationService = Depends(get_curation_service),
) -> Response:
    content = await service.read_pdf(actor=actor, bula_id=bula_id)
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="bula-{bula_id}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{bula_id}/metadata-suggestions", response_model=SharedMetadataSuggestion)
async def suggest_shared_metadata(
    bula_id: UUID,
    response: Response,
    actor: User = Depends(get_current_user),
    service: CurationService = Depends(get_curation_service),
) -> SharedMetadataSuggestion:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.suggest_metadata(actor=actor, bula_id=bula_id)


@router.post("/{bula_id}/{action}", response_model=CurationMutationResponse)
async def decide_shared_bula(
    bula_id: UUID,
    action: str,
    payload: CurationDecision,
    operation_id: UUID = Depends(get_idempotency_key),
    actor: User = Depends(get_current_user),
    service: CurationService = Depends(get_curation_service),
) -> CurationMutationResponse:
    return await service.decide(
        actor=actor,
        bula_id=bula_id,
        action=action,
        payload=payload,
        operation_id=operation_id,
    )
