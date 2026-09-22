from __future__ import annotations

from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel

from do_blitz.codes import is_valid_alias


def _http_https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an http or https URL")
    return value


def _optional_alias(value: str | None) -> str | None:
    if value is None:
        return None
    if not is_valid_alias(value):
        raise ValueError("alias must be 3-32 characters of [0-9a-zA-Z]")
    return value


class HealthOut(BaseModel):
    status: str


class CreateLinkIn(BaseModel):
    url: Annotated[str, AfterValidator(_http_https_url)]
    alias: Annotated[str | None, AfterValidator(_optional_alias)] = None


class LinkOut(BaseModel):
    code: str
    short_url: str
    long_url: str
    created_at: datetime
    hits: int
