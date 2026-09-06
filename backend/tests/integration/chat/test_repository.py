from datetime import datetime, timedelta, timezone
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.chat.models import ChatMessage, ChatRole, RetrievalMode
from app.modules.chat.repository import ChatPersistenceError, ChatRepository


async def create_user(db_session: AsyncSession, *, email: str) -> User:
    user = User(
        full_name="Chat Repository User",
        email=email,
        hashed_password="not-a-real-password-hash",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.anyio
async def test_add_message_preserves_order(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="chat-order@bulaai.com")
    repo = ChatRepository(db=db_session)
    chat_session = await repo.create_session(
        user_id=cast(int, user.id),
        first_question="Como devo tomar este medicamento?",
    )

    first_message = await repo.add_message(
        session_id=chat_session.id,
        role=ChatRole.USER,
        content="Primeira mensagem",
    )
    second_message = await repo.add_message(
        session_id=chat_session.id,
        role=ChatRole.ASSISTANT,
        content="Segunda mensagem",
    )

    history = await repo.get_session_history(session_id=chat_session.id)

    assert first_message.created_at <= second_message.created_at
    assert [message.id for message in history] == [
        first_message.id,
        second_message.id,
    ]


@pytest.mark.anyio
async def test_get_session_history_returns_chronological(
    db_session: AsyncSession,
) -> None:
    user = await create_user(db_session, email="chat-history@bulaai.com")
    repo = ChatRepository(db=db_session)
    chat_session = await repo.create_session(
        user_id=cast(int, user.id),
        first_question="Historico precisa ficar em ordem?",
    )
    older_message = await repo.add_message(
        session_id=chat_session.id,
        role=ChatRole.USER,
        content="Mensagem mais antiga",
    )
    newer_message = await repo.add_message(
        session_id=chat_session.id,
        role=ChatRole.ASSISTANT,
        content="Mensagem mais nova",
    )

    base_time = datetime.now(timezone.utc)
    older_message.created_at = base_time + timedelta(seconds=10)
    newer_message.created_at = base_time
    await db_session.commit()

    history = await repo.get_session_history(session_id=chat_session.id)

    assert [message.id for message in history] == [
        newer_message.id,
        older_message.id,
    ]


@pytest.mark.anyio
async def test_repository_rollback_on_error(db_session: AsyncSession) -> None:
    repo = ChatRepository(db=db_session)
    invalid_session_id = uuid4()

    with pytest.raises(ChatPersistenceError):
        await repo.add_message(
            session_id=invalid_session_id,
            role=ChatRole.USER,
            content="Mensagem sem sessao",
        )

    count_statement = select(func.count()).select_from(ChatMessage)
    result = await db_session.execute(count_statement)

    assert result.scalar_one() == 0


@pytest.mark.anyio
async def test_list_user_sessions_paginated(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="chat-pagination@bulaai.com")
    other_user = await create_user(db_session, email="chat-other@bulaai.com")
    repo = ChatRepository(db=db_session)

    created_sessions = [
        await repo.create_session(
            user_id=cast(int, user.id),
            first_question=f"Pergunta {index}",
        )
        for index in range(5)
    ]
    await repo.create_session(
        user_id=cast(int, other_user.id),
        first_question="Pergunta de outro usuario",
    )

    paginated_sessions = await repo.list_user_sessions(
        user_id=cast(int, user.id),
        limit=2,
        offset=1,
    )

    assert [session.id for session in paginated_sessions] == [
        session.id for session in reversed(created_sessions)
    ][1:3]


@pytest.mark.anyio
async def test_recent_history_returns_latest_messages_in_chronological_order(
    db_session: AsyncSession,
) -> None:
    user = await create_user(db_session, email="chat-recent-history@bulaai.com")
    repo = ChatRepository(db=db_session)
    chat_session = await repo.create_session(
        user_id=cast(int, user.id),
        first_question="Pergunta inicial",
    )
    for turn_number in range(3):
        await repo.add_turn(
            session=chat_session,
            question=f"Pergunta {turn_number}",
            answer=f"Resposta {turn_number}",
            retrieval_mode=RetrievalMode.DENSE,
            source_chunks=[],
        )

    recent_messages = await repo.get_recent_session_history(
        session_id=chat_session.id,
        message_limit=4,
    )

    assert [message.content for message in recent_messages] == [
        "Pergunta 1",
        "Resposta 1",
        "Pergunta 2",
        "Resposta 2",
    ]
