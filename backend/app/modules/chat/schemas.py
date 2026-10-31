from datetime import datetime
from uuid import UUID
from typing import Literal, cast

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    computed_field,
    HttpUrl,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, ChatScope
from app.modules.bulas.models import PublicCatalogScope
from app.modules.rag.retrieval_mode import RetrievalMode

SessionSortOrder = Literal["created_at", "updated_at"]


class ChatMessageCreate(BaseModel):
    role: ChatRole
    content: str
    retrieval_mode: RetrievalMode | None = None


class SourceChunkResponse(BaseModel):
    corpus: Literal["system", "shared", "private"] | None = None
    chunk_id: str | None = None
    bula_id: UUID | None = None
    drug_name: str | None = None
    manufacturer: str | None = None
    presentation: str | None = None
    strength: str | None = None
    source_url: HttpUrl | None = None
    section_title: str
    chunk_text: str
    relevance_score: float = Field(
        validation_alias=AliasChoices("relevance_score", "score")
    )

    @model_serializer(mode="wrap")
    def serialize_source(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        # Keep legacy sources' wire shape; absent new metadata is not fabricated.
        values = cast(dict[str, object], handler(self))
        return {key: value for key, value in values.items() if value is not None}


class SourceBulaResponse(BaseModel):
    corpus: Literal["system", "shared", "private"] | None = None
    bula_id: UUID
    drug_name: str
    manufacturer: str | None = None
    presentation: str | None = None
    strength: str | None = None
    source_url: HttpUrl | None = None


def source_bulas_from_chunks(
    chunks: list[SourceChunkResponse],
) -> list[SourceBulaResponse]:
    sources: dict[UUID, SourceBulaResponse] = {}
    for chunk in chunks:
        if chunk.bula_id is None or chunk.drug_name is None:
            continue
        if chunk.bula_id not in sources:
            sources[chunk.bula_id] = SourceBulaResponse.model_validate(
                chunk.model_dump()
            )
    return list(sources.values())


class ChatMessageResponse(ChatMessageCreate):
    id: UUID
    session_id: UUID
    source_chunks: list[SourceChunkResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def source_bulas(self) -> list[SourceBulaResponse]:
        return source_bulas_from_chunks(self.source_chunks)


class ChatSessionCreate(BaseModel):
    bula_id: UUID | None = None


class ChatSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=50)
    is_pinned: bool | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_changes(self) -> "ChatSessionUpdate":
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError(
                "Provide a title or a pin preference; null is not allowed."
            )
        return self


class ChatSessionDeletedResponse(BaseModel):
    session_id: UUID


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: int
    bula_id: UUID | None
    scope: ChatScope = ChatScope.BULA
    catalog_scope: PublicCatalogScope = PublicCatalogScope.ALL
    title: str
    is_pinned: bool = False
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
            scope=ChatScope(session.scope),
            catalog_scope=PublicCatalogScope(session.catalog_scope),
            title=session.title,
            is_pinned=session.is_pinned,
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
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    mode: RetrievalMode = RetrievalMode.HYBRID

    @field_validator("question")
    @classmethod
    def strip_and_validate_question(cls, value: str) -> str:
        clean_question = value.strip()
        if not clean_question:
            raise ValueError("Question cannot be blank.")

        return clean_question


class CrossBulaAskRequest(AskRequest):
    catalog_scope: PublicCatalogScope = PublicCatalogScope.ALL


class AskResponse(BaseModel):
    session_id: UUID
    answer: str
    retrieval_mode: RetrievalMode
    catalog_scope: PublicCatalogScope | None = None
    source_chunks: list[SourceChunkResponse] = Field(default_factory=list)

    @computed_field
    def source_bulas(self) -> list[SourceBulaResponse]:
        return source_bulas_from_chunks(self.source_chunks)
