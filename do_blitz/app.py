from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from do_blitz.config import Settings, load_settings
from do_blitz.models import CreateLinkIn, HealthOut, LinkOut
from do_blitz.service import create_link, get_link, resolve_link
from do_blitz.store import CodeAlreadyExists, Link, LinkStore, build_store


def _short_url(request: Request, code: str, settings: Settings) -> str:
    base = (settings.public_base_url or str(request.base_url)).rstrip("/")
    return f"{base}/{code}"


def _out(link: Link, request: Request, settings: Settings) -> LinkOut:
    return LinkOut(
        code=link.code,
        short_url=_short_url(request, link.code, settings),
        long_url=link.long_url,
        created_at=link.created_at,
        hits=link.hits,
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

    @app.post("/api/v1/links", response_model=LinkOut, status_code=201)
    def post_link(body: CreateLinkIn, request: Request) -> LinkOut:
        try:
            link = create_link(store, url=body.url, alias=body.alias)
        except CodeAlreadyExists:
            raise HTTPException(status_code=409, detail="alias already in use") from None
        return _out(link, request, settings)

    @app.get("/api/v1/links/{code}", response_model=LinkOut)
    def get_metadata(code: str, request: Request) -> LinkOut:
        link = get_link(store, code)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        return _out(link, request, settings)

    @app.get("/{code}")
    def redirect(code: str) -> RedirectResponse:
        link = resolve_link(store, code)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        return RedirectResponse(url=link.long_url, status_code=302)

    return app


app = create_app()
