from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int = 8000
    log_level: str = "info"
    database_url: str | None = None
    public_base_url: str | None = None
    redis_url: str | None = None
    rate_limit_shorten_per_min: int = 60


def sqlalchemy_url(raw: str) -> str:
    if raw.startswith("postgresql+"):
        return raw
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


def _nonneg_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an int, got {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    env = environ if environ is not None else os.environ
    port_raw = env.get("PORT", "8000")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"PORT must be an int, got {port_raw!r}") from exc
    return Settings(
        port=port,
        log_level=env.get("LOG_LEVEL", "info"),
        database_url=env.get("DATABASE_URL") or None,
        public_base_url=env.get("PUBLIC_BASE_URL") or None,
        redis_url=env.get("REDIS_URL") or None,
        rate_limit_shorten_per_min=_nonneg_int(env, "RATE_LIMIT_SHORTEN_PER_MIN", 60),
    )
