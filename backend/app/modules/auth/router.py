# API endpoints(Request / Response)
from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth import schemas, models
from app.modules.auth.dependencies import get_current_user, get_auth_service
from app.modules.auth.service import (
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_in: schemas.UserCreate, auth_service: AuthService = Depends(get_auth_service)
):
    """
    Registers a new user and returns their profile.
    """
    try:
        return await auth_service.register_new_user(user_in)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )


@router.post("/login", response_model=schemas.Token)
async def login(
    user_in: schemas.UserLogin, auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticates a user and returns a JWT access token.
    """
    try:
        return await auth_service.authenticate_user(
            email=user_in.email,
            password=user_in.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=schemas.UserResponse)
async def get_my_profile(current_user: models.User = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    """
    return current_user
