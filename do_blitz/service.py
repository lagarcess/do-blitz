from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timezone

from do_blitz.cache import RedirectCache
from do_blitz.codes import iter_candidate_codes
from do_blitz.store import CodeAlreadyExists, Link, LinkStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_link(
    store: LinkStore,
    url: str,
    *,
    candidates: Iterable[str] | None = None,
    now: Callable[[], datetime] | None = None,
) -> Link:
    stamp = (now or _utcnow)()
    source = candidates if candidates is not None else iter_candidate_codes()
    last_conflict: str | None = None
    for code in source:
        link = Link(code=code, long_url=url, created_at=stamp, hit_count=0)
        try:
            store.insert(link)
        except CodeAlreadyExists:
            last_conflict = code
            continue
        return link
    raise RuntimeError(f"exhausted short codes (last conflict {last_conflict!r})")


def get_link(store: LinkStore, code: str) -> Link | None:
    return store.get(code)


def resolve_link(store: LinkStore, cache: RedirectCache, code: str) -> Link | None:
    if cache.get(code) is not None:
        return store.increment_hit_count(code)
    link = store.get(code)
    if link is None:
        return None
    cache.set(code, link.long_url)
    return store.increment_hit_count(code)
