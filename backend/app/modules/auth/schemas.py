# Validation (Pydantic)
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=16)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=16)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    
    class Config:
        from_attributes = True 

class Token(BaseModel):
    access_token: str
    token_type: str