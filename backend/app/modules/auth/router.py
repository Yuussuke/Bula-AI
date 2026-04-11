# API endpoints(Request / Response)
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import schemas, service, models
from app.modules.auth.dependencies import get_current_user
from app.core.database import get_db 

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Registers a new user in the system.
    """
    return await service.AUTH_SERVICE.register_new_user(db, user_in)

@router.post("/login", response_model=schemas.Token)
async def login(
    user_in: schemas.UserLogin, 
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user and returns a JWT access token.
    """
    return await service.AUTH_SERVICE.authenticate_user(
        db,
        email=user_in.email,
        password=user_in.password,
    )

@router.get("/me", response_model=schemas.UserResponse)
async def get_my_profile(
    current_user: models.User = Depends(get_current_user)
):
    """
    Protected route. Returns the profile of the currently authenticated user.
    """
    return current_user