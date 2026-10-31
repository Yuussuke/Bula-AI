from fastapi import APIRouter, Depends, Query
from uuid import UUID
from app.core.deps import get_idempotency_key

from app.modules.auth.administration import (
    UserAdministrationService,
)
from app.modules.auth.dependencies import get_user_administration_service, require_admin
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    RoleAssignmentRequest,
    UserResponse,
    RoleAssignmentResponse,
    RoleAssignmentAuditResponse,
)


router = APIRouter(
    prefix="/auth/users", tags=["administration"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[UserResponse])
async def list_users(
    query: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: UserAdministrationService = Depends(get_user_administration_service),
) -> list[UserResponse]:
    return await service.list_users(query=query, limit=limit, offset=offset)


@router.patch("/{user_id}/role", response_model=RoleAssignmentResponse)
async def assign_user_role(
    user_id: int,
    payload: RoleAssignmentRequest,
    operation_id: UUID = Depends(get_idempotency_key),
    actor: User = Depends(require_admin),
    service: UserAdministrationService = Depends(get_user_administration_service),
) -> RoleAssignmentResponse:
    return await service.assign_role(
        actor=actor, user_id=user_id, payload=payload, operation_id=operation_id
    )


@router.get("/{user_id}/role-history", response_model=list[RoleAssignmentAuditResponse])
async def get_role_history(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: UserAdministrationService = Depends(get_user_administration_service),
) -> list[RoleAssignmentAuditResponse]:
    return await service.role_history(user_id=user_id, limit=limit, offset=offset)
