from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from do_blitz.config import Settings, load_settings
from do_blitz.models import HealthOut, LinkOut, ShortenIn
from do_blitz.service import create_link, get_link, resolve_link
from do_blitz.store import Link, LinkStore, build_store


def _short_url(request: Request, code: str, settings: Settings) -> str:
    base = (settings.public_base_url or str(request.base_url)).rstrip("/")
    return f"{base}/api/v1/short/{code}"


def _out(link: Link, request: Request, settings: Settings) -> LinkOut:
    return LinkOut(
        code=link.code,
        shortURL=_short_url(request, link.code, settings),
        longURL=link.long_url,
        created_at=link.created_at,
        hits=link.hit_count,
    )


def create_app(
    store: LinkStore | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    store = store if store is not None else build_store(settings)
    app = FastAPI(title="do-blitz", version="0.1.0")
    app.state.settings = settings
    app.state.store = store

    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:
        store.ping()
        return HealthOut(status="ok")

    @app.post("/api/v1/data/shorten", response_model=LinkOut, status_code=201)
    def shorten(body: ShortenIn, request: Request) -> LinkOut:
        link = create_link(store, url=body.longURL)
        return _out(link, request, settings)

    @app.get("/api/v1/data/{shortCode}", response_model=LinkOut)
    def get_metadata(shortCode: str, request: Request) -> LinkOut:
        link = get_link(store, shortCode)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        return _out(link, request, settings)

    @app.get(
        "/api/v1/short/{shortCode}",
        status_code=status.HTTP_302_FOUND,
        response_class=RedirectResponse,
        responses={
            302: {
                "description": "Found. Location is the original long URL.",
                "headers": {
                    "Location": {
                        "description": "Original long URL",
                        "schema": {"type": "string", "format": "uri"},
                    }
                },
            },
            404: {"description": "Unknown short code"},
        },
    )
    def redirect(shortCode: str) -> RedirectResponse:
        link = resolve_link(store, shortCode)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        return RedirectResponse(url=link.long_url, status_code=302)

    return app


app = create_app()
