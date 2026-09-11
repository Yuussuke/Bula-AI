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


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenWithUser(BaseModel):
    token: Token
    user: UserResponse
