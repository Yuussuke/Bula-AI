from fastapi import HTTPException
from uuid import UUID
import structlog

from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import (
    UserRepository,
    RoleAssignmentConflictError,
    AdministrativeRoleProtectedError,
)
from app.modules.auth.schemas import (
    RoleAssignmentRequest,
    UserResponse,
    RoleAssignmentResponse,
    RoleAssignmentAuditResponse,
)
from app.core.idempotency import IdempotencyConflictError, operation_fingerprint

logger = structlog.get_logger(__name__)


class UserAdministrationService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def list_users(
        self, *, query: str, limit: int, offset: int
    ) -> list[UserResponse]:
        users = await self.repository.search_users(
            query=query, limit=limit, offset=offset
        )
        return [UserResponse.model_validate(user) for user in users]

    async def assign_role(
        self,
        *,
        actor: User,
        user_id: int,
        payload: RoleAssignmentRequest,
        operation_id: UUID,
    ) -> RoleAssignmentResponse:
        if actor.role != UserRole.ADMIN:
            raise HTTPException(403, "Somente administradores podem designar perfis.")
        actor_id = int(actor.id)
        user = await self.repository.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(404, "Usuário não encontrado.")
        request_fingerprint = operation_fingerprint(
            "assign_role", {"user_id": user_id, **payload.model_dump(mode="json")}
        )
        try:
            changed = await self.repository.assign_role(
                user_id=user_id,
                actor=actor,
                previous_role=payload.expected_role,
                assigned_role=UserRole(payload.role),
                reason=payload.reason,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
        except RoleAssignmentConflictError as error:
            raise HTTPException(
                409,
                "O perfil mudou ou já é o solicitado. Atualize a lista de usuários.",
            ) from error
        except AdministrativeRoleProtectedError as error:
            raise HTTPException(
                400, "Esta operação não altera contas administrativas."
            ) from error
        except IdempotencyConflictError as error:
            raise HTTPException(
                409, "Esta chave de operação já foi usada com outro conteúdo."
            ) from error
        logger.info(
            "role_assignment_replayed"
            if changed.replayed
            else "role_assignment_committed",
            actor_id=actor_id,
            user_id=user_id,
            operation_id=str(operation_id),
        )
        return RoleAssignmentResponse(
            **UserResponse.model_validate(changed.user).model_dump(),
            operation_id=operation_id,
            replayed=changed.replayed,
        )

    async def role_history(
        self, *, user_id: int, limit: int, offset: int
    ) -> list[RoleAssignmentAuditResponse]:
        if await self.repository.get_user_by_id(user_id) is None:
            raise HTTPException(404, "Usuário não encontrado.")
        records = await self.repository.role_history(
            user_id=user_id, limit=limit, offset=offset
        )
        return [
            RoleAssignmentAuditResponse.model_validate(record) for record in records
        ]
