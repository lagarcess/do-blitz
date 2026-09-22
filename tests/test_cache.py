from __future__ import annotations

from datetime import datetime, timezone

from do_blitz.cache import MemoryRedirectCache, RedisRedirectCache, build_cache
from do_blitz.config import Settings, load_settings
from do_blitz.service import resolve_link
from do_blitz.store import Link, MemoryLinkStore


def test_load_settings_reads_redis_url() -> None:
    settings = load_settings({"REDIS_URL": "redis://cache:6379/1"})
    assert settings.redis_url == "redis://cache:6379/1"
    assert load_settings({}).redis_url is None


def test_build_cache_memory_without_redis_url() -> None:
    cache = build_cache(Settings())
    assert isinstance(cache, MemoryRedirectCache)


def test_build_cache_redis_when_url_set() -> None:
    cache = build_cache(Settings(redis_url="redis://localhost:6379/0"))
    assert isinstance(cache, RedisRedirectCache)


class BlindGetStore(MemoryLinkStore):
    def get(self, code: str) -> Link | None:
        return None


def test_redirect_cache_hit_skips_store_get() -> None:
    store = BlindGetStore()
    cache = MemoryRedirectCache()
    store.insert(
        Link(
            code="abc123",
            long_url="https://example.com/dest",
            created_at=datetime.now(timezone.utc),
            hit_count=0,
        )
    )
    cache.set("abc123", "https://example.com/dest")
    link = resolve_link(store, cache, "abc123")
    assert link is not None
    assert link.long_url == "https://example.com/dest"
    assert link.hit_count == 1


def test_redirect_db_miss_is_404_and_does_not_fill_cache(client, cache) -> None:
    response = client.get("/api/v1/short/noSuchCode99", follow_redirects=False)
    assert response.status_code == 404
    assert cache.get("noSuchCode99") is None


def test_redirect_db_hit_fills_cache(client, cache) -> None:
    created = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/cached"},
    ).json()
    code = created["code"]
    assert cache.get(code) is None
    redirect = client.get(f"/api/v1/short/{code}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/cached"
    assert cache.get(code) == "https://example.com/cached"
    second = client.get(f"/api/v1/short/{code}", follow_redirects=False)
    assert second.status_code == 302
    assert second.headers["location"] == "https://example.com/cached"
    meta = client.get(f"/api/v1/data/{code}")
    assert meta.json()["hits"] == 2
