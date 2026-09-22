from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from do_blitz.app import create_app
from do_blitz.config import Settings, load_settings
from do_blitz.rate_limit import MemoryRateLimiter, RedisRateLimiter, build_limiter


def test_load_settings_reads_rate_limit() -> None:
    settings = load_settings({"RATE_LIMIT_SHORTEN_PER_MIN": "12"})
    assert settings.rate_limit_shorten_per_min == 12
    assert load_settings({}).rate_limit_shorten_per_min == 60


def test_load_settings_rejects_negative_rate_limit() -> None:
    with pytest.raises(ValueError, match="RATE_LIMIT_SHORTEN_PER_MIN"):
        load_settings({"RATE_LIMIT_SHORTEN_PER_MIN": "-1"})


def test_build_limiter_memory_without_redis_url() -> None:
    limiter = build_limiter(Settings())
    assert isinstance(limiter, MemoryRateLimiter)


def test_build_limiter_redis_when_url_set() -> None:
    limiter = build_limiter(Settings(redis_url="redis://localhost:6379/0"))
    assert isinstance(limiter, RedisRateLimiter)


def test_memory_limiter_resets_after_window() -> None:
    clock = {"t": 0.0}
    limiter = MemoryRateLimiter(now=lambda: clock["t"], window_seconds=60)
    assert limiter.allow("shorten:1.1.1.1", 1) is True
    assert limiter.allow("shorten:1.1.1.1", 1) is False
    clock["t"] = 60.0
    assert limiter.allow("shorten:1.1.1.1", 1) is True


def test_memory_limiter_zero_limit_is_unlimited() -> None:
    limiter = MemoryRateLimiter()
    for _ in range(5):
        assert limiter.allow("shorten:1.1.1.1", 0) is True


def test_shorten_rate_limit_returns_429(store, cache) -> None:
    settings = load_settings({"RATE_LIMIT_SHORTEN_PER_MIN": "2"})
    client = TestClient(create_app(store=store, cache=cache, settings=settings))
    payload = {"longURL": "https://example.com/page"}
    assert client.post("/api/v1/data/shorten", json=payload).status_code == 201
    assert client.post("/api/v1/data/shorten", json=payload).status_code == 201
    response = client.post("/api/v1/data/shorten", json=payload)
    assert response.status_code == 429
    assert response.json() == {
        "detail": "rate limit exceeded: too many shorten requests from this client"
    }
    assert response.headers["retry-after"] == "60"


def test_shorten_rate_limit_is_per_client_ip(store, cache) -> None:
    settings = load_settings({"RATE_LIMIT_SHORTEN_PER_MIN": "1"})
    client = TestClient(create_app(store=store, cache=cache, settings=settings))
    payload = {"longURL": "https://example.com/page"}
    first = client.post(
        "/api/v1/data/shorten",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert first.status_code == 201
    blocked = client.post(
        "/api/v1/data/shorten",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert blocked.status_code == 429
    other = client.post(
        "/api/v1/data/shorten",
        json=payload,
        headers={"X-Forwarded-For": "198.51.100.20"},
    )
    assert other.status_code == 201


def test_openapi_documents_shorten_429(client) -> None:
    spec = client.get("/openapi.json").json()
    assert "429" in spec["paths"]["/api/v1/data/shorten"]["post"]["responses"]
