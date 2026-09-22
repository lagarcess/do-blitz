from __future__ import annotations

import random

from do_blitz.codes import ALPHABET, generate_code, is_valid_alias, iter_candidate_codes
from do_blitz.config import sqlalchemy_url


def test_generate_code_is_base62_of_requested_length() -> None:
    code = generate_code(6, random.Random(0))
    assert code == "SoMUq2"
    assert all(ch in ALPHABET for ch in code)


def test_iter_candidate_codes_lengthens_after_budget() -> None:
    codes = list(
        iter_candidate_codes(
            start_length=4,
            max_length=6,
            attempts_per_length=2,
            rng=random.Random(1),
        )
    )
    assert [len(c) for c in codes] == [4, 4, 5, 5, 6, 6]
    assert all(all(ch in ALPHABET for ch in c) for c in codes)


def test_is_valid_alias() -> None:
    assert is_valid_alias("abc")
    assert is_valid_alias("MyLink1")
    assert not is_valid_alias("ab")
    assert not is_valid_alias("bad-alias")
    assert not is_valid_alias("health")
    assert not is_valid_alias("x" * 33)


def test_sqlalchemy_url_normalizes_postgres_schemes() -> None:
    assert (
        sqlalchemy_url("postgres://u:p@localhost:5432/db")
        == "postgresql+psycopg://u:p@localhost:5432/db"
    )
    assert (
        sqlalchemy_url("postgresql://u:p@localhost:5432/db?sslmode=require")
        == "postgresql+psycopg://u:p@localhost:5432/db?sslmode=require"
    )
    assert sqlalchemy_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
