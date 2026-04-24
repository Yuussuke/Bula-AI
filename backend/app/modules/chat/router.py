from typing import cast

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.schemas import DirectAskRequest, DirectAskResponse
from app.modules.chat.service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/direct-ask", response_model=DirectAskResponse)
async def direct_ask(
    payload: DirectAskRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> DirectAskResponse:
    return await chat_service.answer_question(
        payload=payload,
        user_id=cast(int, current_user.id),
    )
