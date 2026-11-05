"""Sliding-window rate limiting per client.

Kept in process memory, which is correct while the API runs as a single
instance (the free tier). Swap for a Redis-backed limiter before running
more than one instance; the `RateLimiter` interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 100_000):
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: float = 60.0) -> float | None:
        """Record a hit. Return None if allowed, or seconds to wait if not."""
        now = self._clock()
        with self._lock:
            if len(self._hits) >= self._max_keys and key not in self._hits:
                self._evict(now - window_seconds)
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, hits[0] + window_seconds - now)
            hits.append(now)
            return None

    def _evict(self, cutoff: float) -> None:
        stale = [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]
        if len(self._hits) >= self._max_keys:  # under attack: drop the oldest keys
            for key in list(self._hits)[: max(1, self._max_keys // 10)]:
                del self._hits[key]


def client_key(request: Request) -> str:
    # Uvicorn runs with --proxy-headers behind the host's proxy, so this is
    # the real client address. The IP is used in memory only, never logged.
    return request.client.host if request.client else "unknown"


class RateLimit:
    """FastAPI dependency: `Depends(RateLimit("auth"))`."""

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket

    def __call__(self, request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        limit: int = request.app.state.rate_limits[self.bucket]
        wait = limiter.hit(f"{self.bucket}:{client_key(request)}", limit)
        if wait is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(int(wait) + 1)},
            )
