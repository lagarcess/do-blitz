from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from do_blitz.app import create_app
from do_blitz.codes import ALPHABET
from do_blitz.config import Settings
from do_blitz.models import MAX_URL_LEN
from do_blitz.service import create_link
from do_blitz.store import Link, MemoryLinkStore


def test_create_happy_path(client) -> None:
    response = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/page"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["longURL"] == "https://example.com/page"
    assert body["hits"] == 0
    assert body["last_accessed_at"] is None
    assert all(ch in ALPHABET for ch in body["code"])
    assert body["shortURL"] == f"http://testserver/{body['code']}"
    assert body["created_at"]
    assert set(body) == {"code", "shortURL", "longURL", "created_at", "hits", "last_accessed_at"}


def test_redirect_increments_hits(client) -> None:
    created = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/dest"},
    ).json()
    code = created["code"]
    redirect = client.get(f"/api/v1/short/{code}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/dest"
    meta = client.get(f"/api/v1/data/{code}")
    assert meta.status_code == 200
    assert meta.json()["hits"] == 1
    assert meta.json()["last_accessed_at"] is not None
    assert meta.json()["longURL"] == "https://example.com/dest"
    assert meta.json()["code"] == code
    assert meta.json()["shortURL"] == f"http://testserver/{code}"


def test_get_metadata_does_not_redirect(client) -> None:
    created = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/meta"},
    ).json()
    response = client.get(f"/api/v1/data/{created['code']}", follow_redirects=False)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == created["code"]
    assert body["longURL"] == "https://example.com/meta"
    assert body["hits"] == 0
    assert "location" not in response.headers


def test_unknown_code_404(client) -> None:
    assert client.get("/api/v1/data/noSuchCode99").status_code == 404
    assert client.get("/api/v1/short/noSuchCode99", follow_redirects=False).status_code == 404
    assert client.get("/noSuchCode99", follow_redirects=False).status_code == 404


def test_bad_url_422(client) -> None:
    assert (
        client.post("/api/v1/data/shorten", json={"longURL": "ftp://example.com"}).status_code
        == 422
    )
    assert client.post("/api/v1/data/shorten", json={"longURL": "not-a-url"}).status_code == 422
    assert client.post("/api/v1/data/shorten", json={}).status_code == 422
    too_long = "https://example.com/" + ("a" * MAX_URL_LEN)
    assert client.post("/api/v1/data/shorten", json={"longURL": too_long}).status_code == 422
    for bad in (
        "https://@",
        "https://user@/",
        "https://",
        "https://.",
        "http://" + chr(0) + "evil.example",
        "https://example.com/" + chr(0x1F) + "path",
    ):
        response = client.post("/api/v1/data/shorten", json={"longURL": bad})
        assert response.status_code == 422, bad



def test_openapi_documents_redirect_302(client) -> None:
    spec = client.get("/openapi.json").json()
    path = spec["paths"]["/api/v1/short/{shortCode}"]["get"]
    assert "302" in path["responses"]
    root = spec["paths"]["/{code}"]["get"]
    assert "302" in root["responses"]
    assert "404" in root["responses"]
    shorten = spec["paths"]["/api/v1/data/shorten"]["post"]
    assert shorten["responses"]["201"]
    assert "409" in shorten["responses"]
    assert spec["paths"]["/api/v1/data/{shortCode}"]["get"]["responses"]["200"]
    schemas = spec["components"]["schemas"]
    alias = schemas["ShortenIn"]["properties"]["alias"]
    string_schema = next(item for item in alias["anyOf"] if item.get("type") == "string")
    assert string_schema["minLength"] == 3
    assert string_schema["maxLength"] == 32
    assert string_schema["pattern"] == "^[0-9a-zA-Z]+$"
    assert "last_accessed_at" in schemas["LinkOut"]["properties"]


def test_create_with_alias(client) -> None:
    response = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/page", "alias": "promo1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "promo1"
    assert body["shortURL"] == "http://testserver/promo1"
    assert body["longURL"] == "https://example.com/page"
    assert body["hits"] == 0
    assert body["last_accessed_at"] is None


def test_bad_alias_422(client) -> None:
    url = "https://example.com/page"
    assert client.post("/api/v1/data/shorten", json={"longURL": url, "alias": "ab"}).status_code == 422
    assert (
        client.post("/api/v1/data/shorten", json={"longURL": url, "alias": "a" * 33}).status_code
        == 422
    )
    assert (
        client.post("/api/v1/data/shorten", json={"longURL": url, "alias": "my-link"}).status_code
        == 422
    )
    for reserved in ("api", "HEALTH", "Docs", "redoc", "static", "short", "data", "v1"):
        assert (
            client.post("/api/v1/data/shorten", json={"longURL": url, "alias": reserved}).status_code
            == 422
        )


def test_alias_conflict_409(client) -> None:
    first = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/a", "alias": "taken1"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/b", "alias": "taken1"},
    )
    assert second.status_code == 409
    assert second.json() == {"detail": "alias already exists"}


def test_redirect_sets_last_accessed_at(client) -> None:
    created = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/dest"},
    ).json()
    assert created["last_accessed_at"] is None
    code = created["code"]
    redirect = client.get(f"/api/v1/short/{code}", follow_redirects=False)
    assert redirect.status_code == 302
    meta = client.get(f"/api/v1/data/{code}").json()
    assert meta["hits"] == 1
    assert meta["last_accessed_at"] is not None
    datetime.fromisoformat(meta["last_accessed_at"].replace("Z", "+00:00"))


def test_create_retries_after_code_collision() -> None:
    store = MemoryLinkStore()
    store.insert(
        Link(
            code="taken1",
            long_url="https://example.com/first",
            created_at=datetime.now(timezone.utc),
            hit_count=0,
        )
    )
    link = create_link(store, "https://example.com/second", candidates=["taken1", "fresh9"])
    assert link.code == "fresh9"
    assert store.get("fresh9") is not None


def test_create_skips_reserved_random_candidate() -> None:
    store = MemoryLinkStore()
    link = create_link(store, "https://example.com/second", candidates=["health", "fresh9"])
    assert link.code == "fresh9"


def test_root_redirect_increments_hits(client) -> None:
    created = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/root"},
    ).json()
    code = created["code"]
    assert created["shortURL"] == f"http://testserver/{code}"
    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/root"
    meta = client.get(f"/api/v1/data/{code}")
    assert meta.status_code == 200
    assert meta.json()["hits"] == 1
    assert meta.json()["last_accessed_at"] is not None
    assert meta.json()["shortURL"] == f"http://testserver/{code}"


def test_short_url_uses_public_base_and_root_path(store, cache) -> None:
    client = TestClient(
        create_app(
            store=store,
            cache=cache,
            settings=Settings(public_base_url="https://go.example"),
        )
    )
    response = client.post(
        "/api/v1/data/shorten",
        json={"longURL": "https://example.com/page", "alias": "promo1"},
    )
    assert response.status_code == 201
    assert response.json()["shortURL"] == "https://go.example/promo1"


def test_reserved_paths_are_not_treated_as_codes(client, store) -> None:
    now = datetime.now(timezone.utc)
    for name in ("health", "docs", "redoc", "short", "api"):
        store.insert(
            Link(
                code=name,
                long_url="https://example.com/hijack",
                created_at=now,
                hit_count=0,
            )
        )
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    redoc = client.get("/redoc")
    assert redoc.status_code == 200
    assert "text/html" in redoc.headers["content-type"]
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert openapi.json()["paths"]["/api/v1/data/shorten"]["post"]
    assert client.get("/short", follow_redirects=False).status_code == 404
    api = client.get("/api", follow_redirects=False)
    assert api.status_code == 404
    assert "location" not in api.headers
    stolen = client.get("/HEALTH", follow_redirects=False)
    assert stolen.status_code == 404
    assert "location" not in stolen.headers
