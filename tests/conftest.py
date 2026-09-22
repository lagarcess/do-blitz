from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from do_blitz.app import create_app
from do_blitz.cache import MemoryRedirectCache
from do_blitz.config import load_settings
from do_blitz.store import PostgresLinkStore, build_store


@pytest.fixture
def store():
    settings = load_settings()
    built = build_store(settings, allow_memory=True)
    if isinstance(built, PostgresLinkStore):
        built.wipe()
    yield built
    if isinstance(built, PostgresLinkStore):
        built.wipe()


@pytest.fixture
def cache() -> MemoryRedirectCache:
    return MemoryRedirectCache()


@pytest.fixture
def client(store, cache) -> TestClient:
    return TestClient(create_app(store=store, cache=cache))
