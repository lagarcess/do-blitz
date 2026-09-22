# Architecture

TODO: diagram TBD (awaiting Platform + plan lock).

## Package map

- `do_blitz/app.py` — FastAPI factory: health, create, metadata, redirect
- `do_blitz/config.py` — `PORT`, `LOG_LEVEL`, `DATABASE_URL`, `PUBLIC_BASE_URL`
- `do_blitz/models.py` — Pydantic v2 request and metadata payloads
- `do_blitz/codes.py` — base62 alphabet, alias checks, short-then-longer generators
- `do_blitz/service.py` — create / lookup / resolve (hits increment)
- `do_blitz/store.py` — `LinkStore` protocol, `MemoryLinkStore`, `PostgresLinkStore`

There are no update or delete routes. Codes are immutable after insert.

## Diagram

```
TODO
```

## API

| Method | Path | Result |
| --- | --- | --- |
| POST | `/api/v1/links` | 201 metadata. Body `{"url", "alias"}`. |
| GET | `/api/v1/links/{code}` | 200 metadata. Unknown code is 404. |
| GET | `/{code}` | 302 `Location` to the long URL. Increments `hits`. |
| GET | `/health` | 200 `{"status":"ok"}`. |

Metadata fields: `code`, `short_url`, `long_url`, `created_at`, `hits`.

Validation lives at the HTTP boundary (Pydantic):

- `url` must be `http` or `https`
- `alias`, when present, is `[0-9a-zA-Z]`, length 3–32, not a reserved path name
- bad body → 422
- taken alias → 409
- unknown code → 404

Auto codes use `[0-9a-zA-Z]` only. Generation starts at length 6 and grows on collision up to 12.

## Storage

`LinkStore` is the persistence interface. Production uses `PostgresLinkStore` when `DATABASE_URL` is set (SQLAlchemy 2.x + psycopg). `code` is the primary key (unique).

Without `DATABASE_URL` the process uses `MemoryLinkStore` so health and local API tests can run offline. CI sets `DATABASE_URL` and runs against Postgres.

## Scale (BOTE, not encoded in code)

These numbers are planning context. The process does not preallocate 365B rows or 365TB.

- 100M creates/day ≈ 100e6 / 86400 ≈ **1160 writes/s**
- Reads:writes ≈ 10:1 ⇒ about **12k redirects/s** at that create rate
- 10 years at 100M/day ≈ **365B records**
- Row plus indexes is hundreds of bytes. 365B rows is **tens to hundreds of TB**, not something this binary pretends to hold

A 6-character base62 space is 62^6 ≈ 56.8B codes. Collision then lengthens. 7 characters is 62^7 ≈ 3.5T, enough for the 10-year BOTE.

## HA, uniqueness, idempotency

Target deploy (not provisioned here): App Platform, multiple app instances, Managed Postgres.

Concurrency control is the unique constraint on `code`. Two instances that roll the same random code: one insert wins, the other retries with a new code. Two instances that post the same custom alias: one 201, the other 409.

Create is not naturally idempotent. A client that retries after a lost 201 can insert a second code for the same long URL. A client that retries the same alias after a confirmed 201 gets 409. Safe retry is: on unknown outcome, GET `/api/v1/links/{code}` if the alias was chosen, or treat a new auto code as a new link.

`hits` increment is a single `UPDATE … SET hits = hits + 1` per redirect.

## Out of scope

DigitalOcean tokens, App Platform / Managed Postgres provisioning, update/delete, auth.
