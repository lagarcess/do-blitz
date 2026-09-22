from __future__ import annotations

from typing import Protocol

import redis

from do_blitz.config import Settings

CACHE_KEY_PREFIX = "do-blitz:url:"


class RedirectCache(Protocol):
    def get(self, code: str) -> str | None: ...
    def set(self, code: str, long_url: str) -> None: ...


class MemoryRedirectCache:
    def __init__(self) -> None:
        self._urls: dict[str, str] = {}

    def get(self, code: str) -> str | None:
        return self._urls.get(code)

    def set(self, code: str, long_url: str) -> None:
        self._urls[code] = long_url


class RedisRedirectCache:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, code: str) -> str | None:
        value = self._client.get(CACHE_KEY_PREFIX + code)
        if value is None:
            return None
        return str(value)

    def set(self, code: str, long_url: str) -> None:
        self._client.set(CACHE_KEY_PREFIX + code, long_url)


def build_cache(settings: Settings) -> RedirectCache:
    if settings.redis_url:
        return RedisRedirectCache(settings.redis_url)
    return MemoryRedirectCache()
