from __future__ import annotations

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str


# Placeholders for future shortener payloads (stubs only).
class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    code: str
    url: str
