"""Contracts for authenticated workspace navigation, independent of RAG."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.bulas.schemas import PublicCatalogBulaResponse
from app.modules.chat.schemas import ChatSessionResponse


class WorkspaceSearchQuery(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    kind: Literal["all", "chats", "medications"] = "all"
    cursor: str | None = Field(default=None, pattern=r"^[0-4]:[0-9]{1,9}$")
    limit: int = Field(default=15, ge=1, le=20)

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ChatSearchResult(BaseModel):
    kind: Literal["chat"] = "chat"
    session: ChatSessionResponse
    matched_in: Literal["title", "message"]
    message_id: UUID | None = None
    excerpt: str | None = None
    matched_at: datetime


class MedicationSearchResult(BaseModel):
    kind: Literal["medication"] = "medication"
    medication: PublicCatalogBulaResponse


SearchResult = Annotated[
    ChatSearchResult | MedicationSearchResult, Field(discriminator="kind")
]


class WorkspaceSearchPage(BaseModel):
    items: list[SearchResult]
    next_cursor: str | None = None
