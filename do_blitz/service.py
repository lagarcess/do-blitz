from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timezone

from do_blitz.codes import RESERVED_ALIASES, iter_candidate_codes
from do_blitz.store import CodeAlreadyExists, Link, LinkStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_link(
    store: LinkStore,
    url: str,
    alias: str | None = None,
    *,
    candidates: Iterable[str] | None = None,
    now: Callable[[], datetime] | None = None,
) -> Link:
    stamp = (now or _utcnow)()
    if alias is not None:
        link = Link(code=alias, long_url=url, created_at=stamp, hits=0)
        store.insert(link)
        return link

    source = candidates if candidates is not None else iter_candidate_codes()
    last_conflict: str | None = None
    for code in source:
        if code.lower() in RESERVED_ALIASES:
            continue
        link = Link(code=code, long_url=url, created_at=stamp, hits=0)
        try:
            store.insert(link)
        except CodeAlreadyExists:
            last_conflict = code
            continue
        return link
    raise RuntimeError(f"exhausted short codes (last conflict {last_conflict!r})")


def get_link(store: LinkStore, code: str) -> Link | None:
    return store.get(code)


def resolve_link(store: LinkStore, code: str) -> Link | None:
    return store.increment_hits(code)
