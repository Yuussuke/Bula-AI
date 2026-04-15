from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.modules.chat.models import ChatRole, RetrievalMode


class ChatMessageCreate(BaseModel):
    role: ChatRole
    content: str
    retrieval_mode: RetrievalMode | None = None


class ChatMessageResponse(ChatMessageCreate):
    id: UUID
    session_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    bula_id: UUID | None = None


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: int
    bula_id: UUID | None
    created_at: datetime
    updated_at: datetime

    messages: list[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
