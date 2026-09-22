from __future__ import annotations

from do_blitz.codes import ALPHABET
from do_blitz.service import create_link
from do_blitz.store import MemoryLinkStore


def test_create_happy_path(client) -> None:
    response = client.post("/api/v1/links", json={"url": "https://example.com/page"})
    assert response.status_code == 201
    body = response.json()
    assert body["long_url"] == "https://example.com/page"
    assert body["hits"] == 0
    assert all(ch in ALPHABET for ch in body["code"])
    assert body["short_url"] == f"http://testserver/{body['code']}"
    assert body["created_at"]


def test_redirect_increments_hits(client) -> None:
    created = client.post("/api/v1/links", json={"url": "https://example.com/dest"}).json()
    code = created["code"]
    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/dest"
    meta = client.get(f"/api/v1/links/{code}")
    assert meta.status_code == 200
    assert meta.json()["hits"] == 1
    assert meta.json()["long_url"] == "https://example.com/dest"
    assert meta.json()["code"] == code


def test_get_metadata(client) -> None:
    created = client.post(
        "/api/v1/links",
        json={"url": "https://example.com/meta", "alias": None},
    ).json()
    response = client.get(f"/api/v1/links/{created['code']}")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == created["code"]
    assert body["long_url"] == "https://example.com/meta"
    assert body["hits"] == 0
    assert body["short_url"] == f"http://testserver/{created['code']}"


def test_custom_alias_success_conflict_and_invalid(client) -> None:
    ok = client.post(
        "/api/v1/links",
        json={"url": "https://example.com/a", "alias": "MyLink1"},
    )
    assert ok.status_code == 201
    assert ok.json()["code"] == "MyLink1"
    assert ok.json()["short_url"] == "http://testserver/MyLink1"

    conflict = client.post(
        "/api/v1/links",
        json={"url": "https://example.com/b", "alias": "MyLink1"},
    )
    assert conflict.status_code == 409

    invalid = client.post(
        "/api/v1/links",
        json={"url": "https://example.com/c", "alias": "bad-alias"},
    )
    assert invalid.status_code == 422


def test_unknown_code_404(client) -> None:
    assert client.get("/api/v1/links/noSuchCode99").status_code == 404
    assert client.get("/noSuchCode99", follow_redirects=False).status_code == 404


def test_bad_url_422(client) -> None:
    assert client.post("/api/v1/links", json={"url": "ftp://example.com"}).status_code == 422
    assert client.post("/api/v1/links", json={"url": "not-a-url"}).status_code == 422
    assert client.post("/api/v1/links", json={"alias": "abc"}).status_code == 422


def test_create_retries_after_code_collision() -> None:
    store = MemoryLinkStore()
    create_link(store, "https://example.com/first", alias="taken1")
    link = create_link(
        store,
        "https://example.com/second",
        candidates=["taken1", "fresh9"],
    )
    assert link.code == "fresh9"
    assert store.get("fresh9") is not None
