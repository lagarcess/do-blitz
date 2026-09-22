from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient

from do_blitz.app import create_app
from do_blitz.cache import MemoryRedirectCache
from do_blitz.store import MemoryLinkStore, PostgresLinkStore


def _safe_test_database_url() -> str | None:
    """Return a Postgres URL that pytest is allowed to wipe, or None for memory.

    Prefer TEST_DATABASE_URL. DATABASE_URL is used only when ALLOW_TEST_DB_WIPE=1
    and the URL looks like a dedicated test database (_test / test in the name).
    Never wipe an unmarked shared or production DATABASE_URL.
    """
    test_url = os.environ.get("TEST_DATABASE_URL") or None
    if test_url:
        return test_url
    db_url = os.environ.get("DATABASE_URL") or None
    if not db_url:
        return None
    allow = os.environ.get("ALLOW_TEST_DB_WIPE") == "1"
    looks_test = re.search(r"(_test|/test|test_)", db_url, re.IGNORECASE) is not None
    if allow and looks_test:
        return db_url
    return None


@pytest.fixture
def store():
    url = _safe_test_database_url()
    if url is None:
        yield MemoryLinkStore()
        return
    built = PostgresLinkStore(url)
    built.wipe()
    yield built
    built.wipe()


@pytest.fixture
def cache() -> MemoryRedirectCache:
    return MemoryRedirectCache()


@pytest.fixture
def client(store, cache) -> TestClient:
    return TestClient(create_app(store=store, cache=cache))
