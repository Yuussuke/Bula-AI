# API endpoints(Request / Response)
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.modules.auth import schemas, models
from app.modules.auth.dependencies import get_current_user, get_auth_service
from app.modules.auth.service import (
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post("/register", response_model=schemas.TokenWithUser, status_code=status.HTTP_201_CREATED)
async def register(
    response: Response,
    user_in: schemas.UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Registers a new user, automatically logs them in, and returns an access token.
    Sets the refresh token in an HttpOnly cookie.
    """
    try:
        new_user = await auth_service.register_new_user(user_in)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # Auto-login: issue tokens immediately after registration
    token, raw_refresh_token = await auth_service.authenticate_user(
        email=user_in.email,
        password=user_in.password,
    )

    set_refresh_cookie(response, raw_refresh_token)

    return schemas.TokenWithUser(
        token=schemas.Token(
            access_token=token.access_token,
            token_type=token.token_type
        ),
        user=schemas.UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=schemas.TokenWithUser)
async def login(
    response: Response,
    user_in: schemas.UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticates a user. Returns an access token in JSON and sets a
    refresh token in an HttpOnly cookie.
    """
    try:
        token, raw_refresh_token = await auth_service.authenticate_user(
            email=user_in.email,
            password=user_in.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    set_refresh_cookie(response, raw_refresh_token)

    user = await auth_service.get_user_from_token(token.access_token)
    return schemas.TokenWithUser(
        token=schemas.Token(
            access_token=token.access_token,
            token_type=token.token_type
        ),
        user=schemas.UserResponse.model_validate(user),
    )

@router.get("/me", response_model=schemas.UserResponse)
async def get_my_profile(current_user: models.User = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    """
    return current_user

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

def set_refresh_cookie(response: Response, token_value: str) -> None:
    """Sets the HttpOnly refresh token cookie on the response."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token_value,
        httponly=True,
        secure=False,        # Set to True in production (HTTPS)
        samesite="lax",
        path="/auth/refresh",
        max_age=REFRESH_COOKIE_MAX_AGE,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clears the refresh token cookie."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth/refresh")

@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Issues a new access token using the refresh token from the HttpOnly cookie.
    Rotates the refresh token on every successful call.
    """
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    try:
        token, new_raw_refresh_token = await auth_service.refresh_session(raw_refresh_token)
    except InvalidRefreshTokenError:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has expired.",
        )

    set_refresh_cookie(response, new_raw_refresh_token)
    return token

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Revokes the refresh token and clears the cookie.
    Always returns 204 — even if no cookie was present.
    """
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if raw_refresh_token:
        await auth_service.logout(raw_refresh_token)

    clear_refresh_cookie(response)