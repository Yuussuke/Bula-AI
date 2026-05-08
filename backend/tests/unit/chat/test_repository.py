import pytest

from app.modules.chat.models import ChatSession
from app.modules.chat.repository import (
    DEFAULT_CHAT_SESSION_TITLE,
    MAX_CHAT_SESSION_TITLE_LENGTH,
    ChatRepository,
)


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added_objects: list[object] = []
        self.has_committed = False
        self.has_refreshed = False

    def add(self, instance: object) -> None:
        self.added_objects.append(instance)

    async def commit(self) -> None:
        self.has_committed = True

    async def rollback(self) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        _ = instance
        self.has_refreshed = True


@pytest.mark.anyio
async def test_create_session_extracts_title_from_question() -> None:
    db = FakeAsyncSession()
    repo = ChatRepository(db=db)  # type: ignore[arg-type]
    first_question = f"  {'A' * 60}  "

    chat_session = await repo.create_session(
        user_id=1,
        first_question=first_question,
    )

    assert isinstance(chat_session, ChatSession)
    assert chat_session.title == "A" * MAX_CHAT_SESSION_TITLE_LENGTH
    assert db.added_objects == [chat_session]
    assert db.has_committed is True
    assert db.has_refreshed is True


@pytest.mark.anyio
async def test_create_session_uses_default_title_for_blank_question() -> None:
    db = FakeAsyncSession()
    repo = ChatRepository(db=db)  # type: ignore[arg-type]

    chat_session = await repo.create_session(
        user_id=1,
        first_question="   ",
    )

    assert chat_session.title == DEFAULT_CHAT_SESSION_TITLE
