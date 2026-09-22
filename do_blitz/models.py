from __future__ import annotations

from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel, Field

from do_blitz.codes import ALPHABET, ALIAS_MAX_LEN, ALIAS_MIN_LEN, is_reserved_code

MAX_URL_LEN = 2048


def _http_https_url(value: str) -> str:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("url contains control characters")
    if len(value) > MAX_URL_LEN:
        raise ValueError(f"url must be at most {MAX_URL_LEN} characters")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must be an http or https URL")
    host = parsed.hostname
    if not host or host == "." or ".." in host:
        raise ValueError("url must include a usable hostname")
    return value


def _optional_alias(value: str | None) -> str | None:
    if value is None:
        return None
    if not (ALIAS_MIN_LEN <= len(value) <= ALIAS_MAX_LEN):
        raise ValueError(f"alias must be {ALIAS_MIN_LEN} to {ALIAS_MAX_LEN} characters")
    if any(ch not in ALPHABET for ch in value):
        raise ValueError("alias must be base62 [0-9a-zA-Z]")
    if is_reserved_code(value):
        raise ValueError("alias is reserved")
    return value


class HealthOut(BaseModel):
    status: str


class ShortenIn(BaseModel):
    longURL: Annotated[str, AfterValidator(_http_https_url)]
    alias: Annotated[
        str | None,
        Field(
            default=None,
            min_length=ALIAS_MIN_LEN,
            max_length=ALIAS_MAX_LEN,
            pattern=r"^[0-9a-zA-Z]+$",
            description=(
                "Optional custom short code. Base62 [0-9a-zA-Z], 3-32 characters. "
                "Reserved names api, health, docs, short, data, and v1 are rejected "
                "(case-insensitive). Omit to mint a random code."
            ),
            examples=["promo1"],
        ),
        AfterValidator(_optional_alias),
    ] = None


class LinkOut(BaseModel):
    code: str
    shortURL: str
    longURL: str
    created_at: datetime
    hits: int
    last_accessed_at: datetime | None = Field(
        default=None,
        description=(
            "When this short URL was last clicked (successful redirect). "
            "Null until the first redirect. hits is how many times it was clicked."
        ),
    )
