import pytest

from app.modules.chat.usage_guard import ChatCapacityExceededError, ChatUsageGuard
from app.modules.chat.dependencies import require_chat_capacity
from app.modules.auth.models import User
import asyncio


def test_users_share_a_budget_across_chat_paths_but_not_with_each_other() -> None:
    now = [0.0]
    guard = ChatUsageGuard(requests_per_minute=2, clock=lambda: now[0])
    guard.acquire(1)
    with pytest.raises(ChatCapacityExceededError):
        guard.acquire(1)
    guard.acquire(2)
    guard.release(2)
    guard.release(1)
    guard.acquire(1)
    guard.release(1)
    with pytest.raises(ChatCapacityExceededError):
        guard.acquire(1)
    now[0] = 60.0
    guard.acquire(1)
    guard.release(1)
    assert guard.active == {}


@pytest.mark.anyio
@pytest.mark.parametrize("is_cancelled", [False, True])
async def test_request_slot_is_released_when_dependency_is_closed_or_cancelled(
    is_cancelled: bool,
) -> None:
    guard = ChatUsageGuard()
    dependency = require_chat_capacity(current_user=User(id=1), guard=guard)
    await anext(dependency)
    with pytest.raises(ChatCapacityExceededError):
        guard.acquire(1)
    if is_cancelled:
        with pytest.raises(asyncio.CancelledError):
            await dependency.athrow(asyncio.CancelledError())
    else:
        await dependency.aclose()
    guard.acquire(1)
    guard.release(1)
