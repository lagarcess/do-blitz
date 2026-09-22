from __future__ import annotations

from fastapi import FastAPI

from do_blitz.config import load_settings
from do_blitz.models import HealthOut
from do_blitz.store import Store


def create_app() -> FastAPI:
    load_settings()
    app = FastAPI(title="do-blitz", version="0.0.1")
    store = Store()

    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:
        store.ping()
        return HealthOut(status="ok")

    return app


app = create_app()
