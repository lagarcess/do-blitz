from __future__ import annotations

from datetime import datetime, timezone

from do_blitz.codes import ALPHABET
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
    assert all(ch in ALPHABET for ch in body["code"])
    assert body["shortURL"] == f"http://testserver/api/v1/short/{body['code']}"
    assert body["created_at"]
    assert set(body) == {"code", "shortURL", "longURL", "created_at", "hits"}


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
    assert meta.json()["longURL"] == "https://example.com/dest"
    assert meta.json()["code"] == code
    assert meta.json()["shortURL"] == f"http://testserver/api/v1/short/{code}"


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


def test_bad_url_422(client) -> None:
    assert (
        client.post("/api/v1/data/shorten", json={"longURL": "ftp://example.com"}).status_code
        == 422
    )
    assert client.post("/api/v1/data/shorten", json={"longURL": "not-a-url"}).status_code == 422
    assert client.post("/api/v1/data/shorten", json={}).status_code == 422
    too_long = "https://example.com/" + ("a" * MAX_URL_LEN)
    assert client.post("/api/v1/data/shorten", json={"longURL": too_long}).status_code == 422


def test_openapi_documents_redirect_302(client) -> None:
    spec = client.get("/openapi.json").json()
    path = spec["paths"]["/api/v1/short/{shortCode}"]["get"]
    assert "302" in path["responses"]
    assert spec["paths"]["/api/v1/data/shorten"]["post"]["responses"]["201"]
    assert spec["paths"]["/api/v1/data/{shortCode}"]["get"]["responses"]["200"]


def test_create_retries_after_code_collision() -> None:
    store = MemoryLinkStore()
    store.insert(
        Link(
            code="taken1",
            long_url="https://example.com/first",
            created_at=datetime.now(timezone.utc),
            hits=0,
        )
    )
    link = create_link(store, "https://example.com/second", candidates=["taken1", "fresh9"])
    assert link.code == "fresh9"
    assert store.get("fresh9") is not None
