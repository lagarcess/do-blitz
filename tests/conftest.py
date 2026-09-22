from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from do_blitz.app import create_app
from do_blitz.config import load_settings
from do_blitz.store import PostgresLinkStore, build_store


@pytest.fixture
def store():
    built = build_store(load_settings())
    if isinstance(built, PostgresLinkStore):
        built.wipe()
    yield built
    if isinstance(built, PostgresLinkStore):
        built.wipe()


@pytest.fixture
def client(store) -> TestClient:
    return TestClient(create_app(store=store))
