"""Bounded per-user admission for paid chat paths (one application process)."""

from collections import deque
from threading import Lock
from time import monotonic
from collections.abc import Callable


class ChatCapacityExceededError(Exception):
    pass


class ChatUsageGuard:
    def __init__(
        self,
        *,
        requests_per_minute: int = 10,
        max_concurrent: int = 1,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.max_concurrent = max_concurrent
        self.clock = clock
        self.requests: dict[int, deque[float]] = {}
        self.active: dict[int, int] = {}
        self.lock = Lock()
        self.last_cleanup = clock()

    def acquire(self, user_id: int) -> None:
        with self.lock:
            now = self.clock()
            if now - self.last_cleanup >= 60:
                self.requests = {
                    key: values
                    for key, values in self.requests.items()
                    if values and values[-1] > now - 60
                }
                self.last_cleanup = now
            requests = self.requests.setdefault(user_id, deque())
            while requests and requests[0] <= now - 60:
                requests.popleft()
            if (
                self.active.get(user_id, 0) >= self.max_concurrent
                or len(requests) >= self.requests_per_minute
            ):
                raise ChatCapacityExceededError()
            requests.append(now)
            self.active[user_id] = self.active.get(user_id, 0) + 1

    def release(self, user_id: int) -> None:
        with self.lock:
            count = self.active.get(user_id, 0)
            if count <= 1:
                self.active.pop(user_id, None)
            else:
                self.active[user_id] = count - 1
