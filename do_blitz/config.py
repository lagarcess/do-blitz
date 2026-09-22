from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int = 8000
    log_level: str = "info"
    database_url: str | None = None


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
    )
