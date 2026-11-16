from __future__ import annotations

import math
import time
from collections import defaultdict, deque


class FailureLimiter:
    """Блокирует ключ (IP) после max_failures неудач за window секунд."""

    def __init__(self, max_failures: int = 5, window: float = 60.0) -> None:
        self.max_failures = max_failures
        self.window = window
        self._fails: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        dq = self._fails[key]
        while dq and dq[0] <= now - self.window:
            dq.popleft()
        return dq

    def retry_after(self, key: str, now: float | None = None) -> int:
        """0 - можно пробовать, иначе сколько секунд ждать."""
        now = time.time() if now is None else now
        dq = self._prune(key, now)
        if len(dq) >= self.max_failures:
            return max(1, math.ceil(dq[0] + self.window - now))
        if not dq:
            self._fails.pop(key, None)
        return 0

    def register_failure(self, key: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)

    def clear(self) -> None:
        self._fails.clear()