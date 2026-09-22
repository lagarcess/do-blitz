from __future__ import annotations

from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel

MAX_URL_LEN = 2048


def _http_https_url(value: str) -> str:
    if len(value) > MAX_URL_LEN:
        raise ValueError(f"url must be at most {MAX_URL_LEN} characters")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an http or https URL")
    return value


class HealthOut(BaseModel):
    status: str


class ShortenIn(BaseModel):
    longURL: Annotated[str, AfterValidator(_http_https_url)]


class LinkOut(BaseModel):
    code: str
    shortURL: str
    longURL: str
    created_at: datetime
    hits: int
