from __future__ import annotations

import time
from typing import Callable, Protocol

import redis

from do_blitz.config import Settings

RATE_KEY_PREFIX = "do-blitz:rl:"
WINDOW_SECONDS = 60


class RateLimiter(Protocol):
    def allow(self, key: str, limit: int) -> bool: ...


class MemoryRateLimiter:
    def __init__(
        self,
        *,
        now: Callable[[], float] | None = None,
        window_seconds: int = WINDOW_SECONDS,
    ) -> None:
        self._now = now or time.time
        self._window = window_seconds
        self._buckets: dict[str, tuple[int, int]] = {}

    def allow(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return True
        window = int(self._now() // self._window)
        if len(self._buckets) > 1024:
            self._buckets = {k: v for k, v in self._buckets.items() if v[0] >= window}
        current = self._buckets.get(key)
        if current is None or current[0] != window:
            self._buckets[key] = (window, 1)
            return True
        count = current[1] + 1
        self._buckets[key] = (window, count)
        return count <= limit


class RedisRateLimiter:
    def __init__(self, redis_url: str, *, window_seconds: int = WINDOW_SECONDS) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._window = window_seconds

    def allow(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return True
        window = int(time.time() // self._window)
        redis_key = f"{RATE_KEY_PREFIX}{key}:{window}"
        pipe = self._client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, self._window * 2)
        count, _ttl = pipe.execute()
        return int(count) <= limit


def build_limiter(settings: Settings) -> RateLimiter:
    if settings.redis_url:
        return RedisRateLimiter(settings.redis_url)
    return MemoryRateLimiter()
