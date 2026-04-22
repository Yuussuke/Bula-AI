import re
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserBase(BaseModel):
    email: EmailStr
    full_name: str

    @field_validator('email')
    @classmethod
    def email_to_lower(cls, value: str) -> str:
        """ Converts the email to lowercase and removes leading/trailing whitespace """
        return value.lower().strip()


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=64) 

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """ Validates that the password contains at least one uppercase letter, one lowercase letter, one number, and one special character."""
        if not re.search(r"[A-Z]", value):
            raise ValueError("A senha deve conter pelo menos uma letra maiúscula.")
        if not re.search(r"[a-z]", value):
            raise ValueError("A senha deve conter pelo menos uma letra minúscula.")
        if not re.search(r"\d", value):
            raise ValueError("A senha deve conter pelo menos um número.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("A senha deve conter pelo menos um caractere especial.")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    @field_validator('email')
    @classmethod
    def email_to_lower(cls, value: str) -> str:
        return value.lower().strip()


class UserResponse(UserBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenWithUser(BaseModel):
    token: Token
    user: UserResponse
