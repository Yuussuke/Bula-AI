from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, RetrievalMode


class ChatMessageCreate(BaseModel):
    role: ChatRole
    content: str
    retrieval_mode: RetrievalMode | None = None


class SourceChunkResponse(BaseModel):
    section_title: str
    chunk_text: str
    relevance_score: float = Field(
        validation_alias=AliasChoices("relevance_score", "score")
    )


class ChatMessageResponse(ChatMessageCreate):
    id: UUID
    session_id: UUID
    source_chunks: list[SourceChunkResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    bula_id: UUID | None = None


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: int
    bula_id: UUID | None
    title: str
    created_at: datetime
    updated_at: datetime

    messages: list[ChatMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_session(
        cls,
        session: ChatSession,
        *,
        messages: list[ChatMessage] | None = None,
    ) -> "ChatSessionResponse":
        return cls(
            id=session.id,
            user_id=session.user_id,
            bula_id=session.bula_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[
                ChatMessageResponse.model_validate(message)
                for message in messages or []
            ],
        )


class DirectAskRequest(BaseModel):
    question: str


class DirectAskResponse(BaseModel):
    answer: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    retrieval_mode: RetrievalMode = RetrievalMode.DENSE

    @field_validator("question")
    @classmethod
    def strip_and_validate_question(cls, value: str) -> str:
        clean_question = value.strip()
        if not clean_question:
            raise ValueError("Question cannot be blank.")

        return clean_question


class AskResponse(BaseModel):
    session_id: UUID
    answer: str
    source_chunks: list[SourceChunkResponse] = Field(default_factory=list)
