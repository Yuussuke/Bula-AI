"""Merge bounded database pages in the declared navigation relevance order."""

import re
import unicodedata
from typing import Literal

from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.schemas import (
    PublicCatalogBulaResponse,
    PublicCatalogSearchQuery,
)
from app.modules.chat.repository import ChatRepository
from app.modules.chat.schemas import ChatSessionResponse
from app.modules.chat.search_schemas import (
    ChatSearchResult,
    MedicationSearchResult,
    SearchResult,
    WorkspaceSearchPage,
    WorkspaceSearchQuery,
)


class WorkspaceSearchService:
    def __init__(
        self, *, chat_repository: ChatRepository, bula_repository: BulaRepository
    ) -> None:
        self.chat_repository = chat_repository
        self.bula_repository = bula_repository

    async def search(
        self, *, user_id: int, filters: WorkspaceSearchQuery
    ) -> WorkspaceSearchPage:
        stage, offset = (0, 0)
        if filters.cursor is not None:
            stage, offset = (int(value) for value in filters.cursor.split(":"))
        items: list[SearchResult] = []
        positions: list[str] = []
        # Prefix titles, prefix drug names, recent user messages, then name/title substrings.
        for bucket in range(stage, 5):
            is_medication_bucket = bucket in (1, 3)
            if (filters.kind == "chats" and is_medication_bucket) or (
                filters.kind == "medications" and not is_medication_bucket
            ):
                continue
            start = offset if bucket == stage else 0
            remaining = filters.limit + 1 - len(items)
            results = await self._search_bucket(
                bucket=bucket,
                user_id=user_id,
                query=filters.query,
                limit=remaining,
                offset=start,
            )
            items.extend(results)
            positions.extend(
                f"{bucket}:{start + index}" for index in range(len(results))
            )
            if len(items) > filters.limit:
                break
        return WorkspaceSearchPage(
            items=items[: filters.limit],
            next_cursor=positions[filters.limit]
            if len(items) > filters.limit
            else None,
        )

    async def _search_bucket(
        self,
        *,
        bucket: int,
        user_id: int,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SearchResult]:
        if bucket in (1, 3):
            medications, _ = await self.bula_repository.search_public_catalog(
                filters=PublicCatalogSearchQuery(
                    query=query, limit=limit, offset=offset
                ),
                name_match="word_prefix" if bucket == 1 else "substring",
            )
            return [
                MedicationSearchResult(
                    medication=PublicCatalogBulaResponse.from_bula(bula)
                )
                for bula in medications
            ]
        match: Literal["title_prefix", "message_prefix", "title_substring"] = (
            "title_prefix"
            if bucket == 0
            else "message_prefix"
            if bucket == 2
            else "title_substring"
        )
        matches = await self.chat_repository.search_user_history(
            user_id=user_id,
            query=query,
            match=match,
            limit=limit,
            offset=offset,
        )
        return [
            ChatSearchResult(
                session=ChatSessionResponse.from_session(session),
                matched_in="message" if message else "title",
                message_id=message.id if message else None,
                excerpt=self._excerpt(message.content, query) if message else None,
                matched_at=message.created_at if message else session.updated_at,
            )
            for session, message in matches
        ]

    def _excerpt(self, content: str, query: str) -> str:
        normalized = "".join(
            character
            for character in unicodedata.normalize("NFD", content)
            if not unicodedata.combining(character)
        )
        term = "".join(
            character
            for character in unicodedata.normalize("NFD", query.split()[0])
            if not unicodedata.combining(character)
        )
        match = re.search(r"(?<!\w)" + re.escape(term), normalized, re.IGNORECASE)
        start = max(0, match.start() - 45) if match else 0
        end = min(len(content), start + 180)
        return (
            ("…" if start else "")
            + content[start:end].strip()
            + ("…" if end < len(content) else "")
        )
