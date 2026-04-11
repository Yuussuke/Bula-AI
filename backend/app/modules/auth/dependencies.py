from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import service
from app.core.database import get_db 

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency that delegates token validation to the service layer.
    """

    return await service.AUTH_SERVICE.get_user_from_token(db, credentials.credentials)