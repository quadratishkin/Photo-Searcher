from __future__ import annotations

from collections import deque
from typing import Deque, Generic, TypeVar


QueueItem = TypeVar("QueueItem")


class RequestQueue(Generic[QueueItem]):
    def __init__(self, limit: int = 50) -> None:
        self.limit = limit
        self._queue: Deque[QueueItem] = deque()

    def addRequest(self, request: QueueItem) -> bool:
        if len(self._queue) >= self.limit:
            return False
        self._queue.append(request)
        return True

    def getNextRequest(self) -> QueueItem | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def getQueueSize(self) -> int:
        return len(self._queue)
