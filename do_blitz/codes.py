from __future__ import annotations

import random
import re
from collections.abc import Iterator

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALIAS_MIN_LEN = 3
ALIAS_MAX_LEN = 32
INITIAL_CODE_LENGTH = 6
MAX_CODE_LENGTH = 12
ATTEMPTS_PER_LENGTH = 8
ALIAS_RE = re.compile(rf"^[{re.escape(ALPHABET)}]{{{ALIAS_MIN_LEN},{ALIAS_MAX_LEN}}}$")
RESERVED_ALIASES = frozenset({"health", "api", "docs", "redoc", "openapi"})


def generate_code(length: int, rng: random.Random | None = None) -> str:
    if length < 1:
        raise ValueError("length must be >= 1")
    choose = rng.choice if rng is not None else random.SystemRandom().choice
    return "".join(choose(ALPHABET) for _ in range(length))


def iter_candidate_codes(
    *,
    start_length: int = INITIAL_CODE_LENGTH,
    max_length: int = MAX_CODE_LENGTH,
    attempts_per_length: int = ATTEMPTS_PER_LENGTH,
    rng: random.Random | None = None,
) -> Iterator[str]:
    source = rng if rng is not None else random.SystemRandom()
    for length in range(start_length, max_length + 1):
        for _ in range(attempts_per_length):
            yield generate_code(length, source)


def is_valid_alias(value: str) -> bool:
    return bool(ALIAS_RE.fullmatch(value)) and value.lower() not in RESERVED_ALIASES
