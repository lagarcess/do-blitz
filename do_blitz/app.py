from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from do_blitz.cache import RedirectCache, build_cache
from do_blitz.config import Settings, load_settings
from do_blitz.models import HealthOut, LinkOut, ShortenIn
from do_blitz.rate_limit import RateLimiter, WINDOW_SECONDS, build_limiter
from do_blitz.service import create_link, get_link, resolve_link
from do_blitz.store import Link, LinkStore, build_store


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


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
    cache: RedirectCache | None = None,
    limiter: RateLimiter | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    store = store if store is not None else build_store(settings)
    cache = cache if cache is not None else build_cache(settings)
    limiter = limiter if limiter is not None else build_limiter(settings)
    app = FastAPI(title="do-blitz", version="0.1.0")
    app.state.settings = settings
    app.state.store = store
    app.state.cache = cache
    app.state.limiter = limiter

    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:
        store.ping()
        return HealthOut(status="ok")

    @app.post(
        "/api/v1/data/shorten",
        response_model=LinkOut,
        status_code=201,
        responses={
            429: {"description": "Too many shorten requests from this client IP."},
        },
    )
    def shorten(body: ShortenIn, request: Request) -> LinkOut:
        ip = _client_ip(request)
        if not limiter.allow(f"shorten:{ip}", settings.rate_limit_shorten_per_min):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded: too many shorten requests from this client",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
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
            404: {"description": "Invalid short URL. Code is not in the database."},
        },
    )
    def redirect(shortCode: str) -> RedirectResponse:
        link = resolve_link(store, cache, shortCode)
        if link is None:
            raise HTTPException(status_code=404, detail="not found")
        return RedirectResponse(url=link.long_url, status_code=302)

    return app


app = create_app()
