from __future__ import annotations

from uuid import UUID
import structlog

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import ValidationError, HttpUrl

from app.modules.bulas.repository import BulaRepository
from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, ChatScope
from app.modules.bulas.models import Bula
from app.modules.chat.repository import ChatRepository
from app.modules.chat.schemas import (
    AskRequest,
    AskResponse,
    DirectAskRequest,
    DirectAskResponse,
    SourceChunkResponse,
)
from app.modules.rag.chain import RAGChainFactory, NO_CONTEXT_MESSAGE


class ChatChainOutputError(RuntimeError):
    """Raised when a RAG chain returns an invalid shape."""


class PublishedSourceIntegrityError(RuntimeError):
    """Published-document provenance violates a repository invariant."""


class ChatSessionNotFoundError(Exception):
    """Raised when a chat session is unavailable to the current user."""


class QueryableBulaNotFoundError(Exception):
    """Raised when a bula cannot be queried by the current user."""


class DirectAskUnavailableError(Exception):
    """Raised while the legacy direct-ask endpoint remains unavailable."""


class PublishedSourcesChangedError(Exception):
    """Source publication changed while the answer was being prepared."""


MAX_PRIOR_CHAT_TURNS = 10
MAX_PRIOR_CHAT_MESSAGES = MAX_PRIOR_CHAT_TURNS * 2
logger = structlog.get_logger(__name__)


class ChatService:
    def __init__(
        self,
        *,
        chat_repository: ChatRepository,
        bula_repository: BulaRepository,
        chain_factory: RAGChainFactory,
    ) -> None:
        self.chat_repository = chat_repository
        self.bula_repository = bula_repository
        self.chain_factory = chain_factory

    async def ask_cross_bula_question(
        self, *, payload: AskRequest, user_id: int
    ) -> AskResponse:
        answer, source_chunks = await self._answer_cross_bula(payload=payload)
        chat_session, _, _ = await self.chat_repository.create_session_with_messages(
            user_id=user_id,
            bula_id=None,
            scope=ChatScope.CROSS_BULA,
            first_question=payload.question,
            answer=answer,
            retrieval_mode=payload.mode,
            source_chunks=self._serialize_source_chunks(source_chunks),
        )
        return AskResponse(
            session_id=chat_session.id,
            answer=answer,
            retrieval_mode=payload.mode,
            source_chunks=source_chunks,
        )

    def _published_source_metadata(self, bula: Bula) -> dict[str, str]:
        publication = bula.system_publication
        if publication is None:
            raise PublishedSourceIntegrityError(
                "Published source is missing its provenance."
            )
        return {
            "drug_name": bula.drug_name,
            "manufacturer": publication.manufacturer,
            "presentation": publication.presentation,
            "strength": publication.strength,
            "source_url": str(HttpUrl(publication.canonical_source_url)),
            "content_sha256": publication.sha256_checksum,
        }

    async def _answer_cross_bula(
        self, *, payload: AskRequest, chat_history: list[BaseMessage] | None = None
    ) -> tuple[str, list[SourceChunkResponse]]:
        bulas = await self.bula_repository.list_queryable_system_bulas()
        sources = {bula.id: self._published_source_metadata(bula) for bula in bulas}
        if not sources:
            logger.info(
                "rag_cross_bula_empty_corpus",
                retrieval_status="not_run",
                requested_mode=payload.mode.value,
            )
            return NO_CONTEXT_MESSAGE, []
        chain = self.chain_factory.build_cross_bula_chain(
            mode=payload.mode, sources=sources
        )
        chain_result = await chain.ainvoke(
            {"question": payload.question, "chat_history": chat_history or []}
        )
        answer, source_chunks = self._parse_chain_result(chain_result)
        for chunk in source_chunks:
            if not chunk.chunk_id or chunk.bula_id not in sources:
                raise ChatChainOutputError(
                    "Cross-bula response contains an unidentified source."
                )
            canonical_source = sources[chunk.bula_id]
            if any(
                str(getattr(chunk, key)) != value
                for key, value in canonical_source.items()
                if key != "content_sha256"
            ):
                raise ChatChainOutputError(
                    "Cross-bula response contains inconsistent source metadata."
                )
        if source_chunks:
            selected_bula_ids = {
                chunk.bula_id for chunk in source_chunks if chunk.bula_id is not None
            }
            current_bulas = await self.bula_repository.list_queryable_system_bulas(
                bula_ids=sorted(selected_bula_ids)
            )
            current_sources = {
                bula.id: self._published_source_metadata(bula) for bula in current_bulas
            }
            if any(
                current_sources.get(chunk.bula_id) != sources[chunk.bula_id]
                for chunk in source_chunks
                if chunk.bula_id is not None
            ):
                raise PublishedSourcesChangedError()
        return answer, source_chunks

    async def ask_bula_question(
        self,
        *,
        bula_id: UUID,
        payload: AskRequest,
        user_id: int,
    ) -> AskResponse:
        bula = await self.bula_repository.get_queryable_by_id_for_user(
            bula_id=bula_id,
            user_id=user_id,
        )
        if bula is None:
            raise QueryableBulaNotFoundError()

        chain = self.chain_factory.build_chain(bula_id=bula_id, mode=payload.mode)
        chain_result = await chain.ainvoke(
            {
                "question": payload.question,
                "drug_name": bula.drug_name,
            }
        )
        answer, source_chunks = self._parse_chain_result(chain_result)

        chat_session, _, _ = await self.chat_repository.create_session_with_messages(
            user_id=user_id,
            bula_id=bula_id,
            first_question=payload.question,
            answer=answer,
            retrieval_mode=payload.mode,
            source_chunks=self._serialize_source_chunks(source_chunks),
        )

        return AskResponse(
            session_id=chat_session.id,
            answer=answer,
            retrieval_mode=payload.mode,
            source_chunks=source_chunks,
        )

    async def continue_session(
        self,
        *,
        session_id: UUID,
        payload: AskRequest,
        user_id: int,
    ) -> AskResponse:
        chat_session = await self.chat_repository.get_session_for_user(
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ChatSessionNotFoundError()

        if chat_session.scope == ChatScope.CROSS_BULA.value:
            previous_messages = await self.chat_repository.get_recent_session_history(
                session_id=session_id, message_limit=MAX_PRIOR_CHAT_MESSAGES
            )
            answer, source_chunks = await self._answer_cross_bula(
                payload=payload,
                chat_history=self._build_chat_history(previous_messages),
            )
            await self.chat_repository.add_turn(
                session=chat_session,
                question=payload.question,
                answer=answer,
                retrieval_mode=payload.mode,
                source_chunks=self._serialize_source_chunks(source_chunks),
            )
            return AskResponse(
                session_id=session_id,
                answer=answer,
                retrieval_mode=payload.mode,
                source_chunks=source_chunks,
            )
        if chat_session.bula_id is None:
            raise ChatSessionNotFoundError()

        bula = await self.bula_repository.get_queryable_by_id_for_user(
            bula_id=chat_session.bula_id,
            user_id=user_id,
        )
        if bula is None:
            raise ChatSessionNotFoundError()

        previous_messages = await self.chat_repository.get_recent_session_history(
            session_id=session_id,
            message_limit=MAX_PRIOR_CHAT_MESSAGES,
        )
        chat_history = self._build_chat_history(previous_messages)
        chain = self.chain_factory.build_chain(
            bula_id=chat_session.bula_id, mode=payload.mode
        )
        chain_result = await chain.ainvoke(
            {
                "question": payload.question,
                "drug_name": bula.drug_name,
                "chat_history": chat_history,
            }
        )
        answer, source_chunks = self._parse_chain_result(chain_result)

        await self.chat_repository.add_turn(
            session=chat_session,
            question=payload.question,
            answer=answer,
            retrieval_mode=payload.mode,
            source_chunks=self._serialize_source_chunks(source_chunks),
        )
        return AskResponse(
            session_id=chat_session.id,
            answer=answer,
            retrieval_mode=payload.mode,
            source_chunks=source_chunks,
        )

    async def list_sessions_for_user(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
        scope: ChatScope | None = None,
        bula_id: UUID | None = None,
    ) -> list[ChatSession]:
        return await self.chat_repository.list_user_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset,
            scope=scope,
            bula_id=bula_id,
        )

    async def get_session_with_history(
        self,
        *,
        session_id: UUID,
        user_id: int,
    ) -> tuple[ChatSession, list[ChatMessage]]:
        chat_session = await self.chat_repository.get_session_for_user(
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ChatSessionNotFoundError()

        messages = await self.chat_repository.get_session_history(
            session_id=session_id,
        )
        return chat_session, messages

    async def answer_question(
        self,
        payload: DirectAskRequest,
        user_id: int,
    ) -> DirectAskResponse:
        """
        Legacy placeholder kept while the first grounded endpoint is introduced.
        Medication answers must flow through the bula-scoped RAG endpoint.
        """
        _ = payload
        _ = user_id
        raise DirectAskUnavailableError()

    def _parse_chain_result(
        self,
        chain_result: dict[str, object],
    ) -> tuple[str, list[SourceChunkResponse]]:
        answer = str(chain_result.get("answer", "")).strip()
        if not answer:
            raise ChatChainOutputError("RAG chain returned an empty answer.")

        raw_source_chunks = chain_result.get("source_chunks", [])
        if not isinstance(raw_source_chunks, list):
            raise ChatChainOutputError("RAG chain returned invalid source_chunks.")

        try:
            source_chunks = [
                SourceChunkResponse.model_validate(source_chunk)
                for source_chunk in raw_source_chunks
            ]
        except ValidationError as exc:
            raise ChatChainOutputError(
                "RAG chain returned invalid source data."
            ) from exc

        return answer, source_chunks

    def _serialize_source_chunks(
        self,
        source_chunks: list[SourceChunkResponse],
    ) -> list[dict[str, str | float]]:
        return [
            source_chunk.model_dump(mode="json", exclude_none=True)
            for source_chunk in source_chunks
        ]

    def _build_chat_history(
        self,
        messages: list[ChatMessage],
    ) -> list[BaseMessage]:
        complete_turns: list[tuple[ChatMessage, ChatMessage]] = []
        pending_user_message: ChatMessage | None = None

        for message in messages:
            if message.role == ChatRole.USER:
                pending_user_message = message
                continue

            if pending_user_message is None:
                continue

            complete_turns.append((pending_user_message, message))
            pending_user_message = None

        chat_history: list[BaseMessage] = []
        for user_message, assistant_message in complete_turns[-MAX_PRIOR_CHAT_TURNS:]:
            chat_history.append(HumanMessage(content=user_message.content))
            chat_history.append(AIMessage(content=assistant_message.content))

        return chat_history
