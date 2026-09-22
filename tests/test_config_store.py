import pytest

from do_blitz.config import Settings
from do_blitz.store import build_store


def test_build_store_requires_database_url() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        build_store(Settings())
