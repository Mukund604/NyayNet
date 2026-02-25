"""Rate limiting for API calls."""

import time
from collections import deque
from threading import Lock


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._calls: deque[float] = deque()
        self._lock = Lock()

    def acquire(self) -> bool:
        """Try to acquire a rate limit token. Returns True if allowed."""
        with self._lock:
            now = time.monotonic()
            # Remove expired entries
            while self._calls and (now - self._calls[0]) >= self.period_seconds:
                self._calls.popleft()

            if len(self._calls) < self.max_calls:
                self._calls.append(now)
                return True
            return False

    def wait_and_acquire(self) -> None:
        """Block until a rate limit token is available."""
        while not self.acquire():
            with self._lock:
                if self._calls:
                    wait_time = self.period_seconds - (time.monotonic() - self._calls[0])
                    wait_time = max(wait_time, 0.1)
                else:
                    wait_time = 0.1
            time.sleep(wait_time)

    @property
    def remaining(self) -> int:
        """Number of remaining calls in the current window."""
        with self._lock:
            now = time.monotonic()
            while self._calls and (now - self._calls[0]) >= self.period_seconds:
                self._calls.popleft()
            return self.max_calls - len(self._calls)
