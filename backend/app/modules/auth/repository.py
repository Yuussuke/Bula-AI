import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import cast
from dataclasses import dataclass
from uuid import UUID
import structlog

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken, User, UserRole, UserRoleAssignment
from app.core.idempotency import IdempotencyConflictError

logger = structlog.get_logger(__name__)


class UserAlreadyExistsRepositoryError(Exception):
    """Raised when a user cannot be created because the email already exists."""


class RefreshTokenCreationError(Exception):
    """Raised when a refresh token cannot be persisted."""


class RoleAssignmentConflictError(Exception):
    """The expected role is stale or would not change the account."""


class AdministrativeRoleProtectedError(Exception):
    """Administrative accounts are managed outside the designation endpoint."""


@dataclass(frozen=True)
class RoleMutationResult:
    user: User
    replayed: bool


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_users(self, *, query: str, limit: int, offset: int) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.email.contains(query.strip().lower(), autoescape=True))
            .order_by(User.email, User.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def assign_role(
        self,
        *,
        user_id: int,
        actor: User,
        previous_role: UserRole,
        assigned_role: UserRole,
        reason: str,
        operation_id: UUID,
        request_fingerprint: str,
    ) -> RoleMutationResult:
        actor_id = int(actor.id)
        try:
            replay = await self.replay_role_assignment(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            user = await self.db.scalar(
                select(User)
                .where(User.id == user_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            replay = await self.replay_role_assignment(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            if user is None:
                raise RoleAssignmentConflictError()
            if user.role == UserRole.ADMIN:
                raise AdministrativeRoleProtectedError()
            if user.role != previous_role or user.role == assigned_role:
                raise RoleAssignmentConflictError()
            await self.db.execute(
                update(User).where(User.id == user_id).values(role=assigned_role)
            )
            self.db.add(
                UserRoleAssignment(
                    user_id=user_id,
                    actor_id=actor_id,
                    previous_role=previous_role.value,
                    assigned_role=assigned_role.value,
                    reason=reason,
                    actor_name=actor.full_name,
                    actor_role=actor.role.value,
                    operation_id=operation_id,
                    request_fingerprint=request_fingerprint,
                )
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            replay = await self.replay_role_assignment(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            raise
        except BaseException:
            await self.db.rollback()
            raise
        return RoleMutationResult(user=user, replayed=False)

    async def replay_role_assignment(
        self, *, actor_id: int, operation_id: UUID, request_fingerprint: str
    ) -> RoleMutationResult | None:
        assignment = await self.db.scalar(
            select(UserRoleAssignment).where(
                UserRoleAssignment.actor_id == actor_id,
                UserRoleAssignment.operation_id == operation_id,
            )
        )
        if assignment is None:
            return None
        if assignment.request_fingerprint != request_fingerprint:
            logger.warning(
                "role_operation_key_conflict",
                actor_id=actor_id,
                operation_id=str(operation_id),
                requested_fingerprint=request_fingerprint,
                recorded_fingerprint=assignment.request_fingerprint,
            )
            raise IdempotencyConflictError()
        user = await self.db.scalar(
            select(User)
            .where(User.id == assignment.user_id)
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise RoleAssignmentConflictError()
        await self.db.commit()
        return RoleMutationResult(user=user, replayed=True)

    async def role_history(
        self, *, user_id: int, limit: int, offset: int
    ) -> list[UserRoleAssignment]:
        result = await self.db.execute(
            select(UserRoleAssignment)
            .where(UserRoleAssignment.user_id == user_id)
            .order_by(UserRoleAssignment.created_at.desc(), UserRoleAssignment.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Fetches a user from the database by their email address.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Fetches a user from the database by their primary key (ID).
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def create_user(
        self,
        full_name: str,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """
        Creates and persists a new user record in the database.
        Returns the newly created User instance.
        """
        db_user = User(
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        self.db.add(db_user)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise UserAlreadyExistsRepositoryError() from exc

        await self.db.refresh(db_user)
        return db_user


def _hash_token(token: str) -> str:
    """Returns a SHA-256 hash of the token string for secure storage and comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int, expires_in_days: int = 30) -> str:
        """Creates a new refresh token, saves the hash, and returns the raw token."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        for attempt in range(3):
            raw_token = secrets.token_urlsafe(48)
            hashed_token = _hash_token(raw_token)

            refresh_token = RefreshToken(
                token=hashed_token,
                user_id=user_id,
                expires_at=expires_at,
            )
            self.db.add(refresh_token)
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                if attempt == 2:
                    raise RefreshTokenCreationError()
            else:
                return raw_token

        raise RefreshTokenCreationError()

    async def get_valid_token(self, raw_token_value: str) -> RefreshToken | None:
        """Returns the token only if it exists, is not revoked, and has not expired."""

        hashed_token = _hash_token(raw_token_value)

        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == hashed_token,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Marks a refresh token as revoked (used during logout or rotation)."""
        token_id = cast(int, token.id)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(is_revoked=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def consume_atomically(self, raw_token_value: str) -> RefreshToken | None:
        """
        Atomically checks if the token is valid and revokes it in a single database transaction.
        """
        hashed_token = _hash_token(raw_token_value)

        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.token == hashed_token,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .values(is_revoked=True)
            .returning(RefreshToken)
        )

        result = await self.db.execute(stmt)
        token = result.scalar_one_or_none()

        if token:
            await self.db.commit()

        return token
