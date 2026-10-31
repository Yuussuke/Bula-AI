from typing import Literal
from uuid import UUID
from datetime import datetime

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.modules.auth.models import UserRole

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64


class RoleAssignmentRequest(BaseModel):
    role: Literal["user", "contributor", "reviewer"]
    expected_role: UserRole
    reason: str = Field(min_length=3, max_length=1000)
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class UserBase(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, value: str) -> str:
        """Converts the email to lowercase and removes leading/trailing whitespace"""
        return value.lower().strip()


class UserCreate(UserBase):
    full_name: str
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    model_config = ConfigDict(extra="forbid")


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, value: str) -> str:
        return value.lower().strip()


class UserResponse(UserBase):
    id: int
    name: str = Field(validation_alias=AliasChoices("name", "full_name"))
    role: UserRole

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RoleAssignmentResponse(UserResponse):
    operation_id: UUID
    replayed: bool


class RoleAssignmentAuditResponse(BaseModel):
    id: UUID
    user_id: int
    actor_id: int | None
    actor_name: str | None
    actor_role: str | None
    previous_role: UserRole
    assigned_role: UserRole
    reason: str
    operation_id: UUID | None
    request_fingerprint: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenWithUser(BaseModel):
    token: Token
    user: UserResponse
