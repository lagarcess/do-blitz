from __future__ import annotations

from tests.conftest import _safe_test_database_url


def test_safe_url_prefers_test_database_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://u:p@localhost:5432/do_blitz_test",
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/prod")
    assert _safe_test_database_url().endswith("/do_blitz_test")


def test_safe_url_ignores_prod_database_url(monkeypatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/prod")
    monkeypatch.delenv("ALLOW_TEST_DB_WIPE", raising=False)
    assert _safe_test_database_url() is None


def test_safe_url_allows_marked_test_db_with_flag(monkeypatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://u:p@localhost:5432/do_blitz_test",
    )
    monkeypatch.setenv("ALLOW_TEST_DB_WIPE", "1")
    assert _safe_test_database_url() is not None
