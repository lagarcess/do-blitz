# Architecture

TODO: diagram TBD (awaiting Platform + plan lock).

## Package map

- `do_blitz/app.py` — FastAPI factory: health, shorten, metadata, redirect
- `do_blitz/config.py` — `PORT`, `LOG_LEVEL`, `DATABASE_URL`, `PUBLIC_BASE_URL`
- `do_blitz/models.py` — Pydantic v2 request and metadata payloads (`longURL` / `shortURL`)
- `do_blitz/codes.py` — base62 alphabet and short-then-longer generators
- `do_blitz/service.py` — create / lookup / resolve (hits increment)
- `do_blitz/store.py` — `LinkStore` protocol, `MemoryLinkStore`, `PostgresLinkStore`

There are no PUT, PATCH, or DELETE routes. Codes are immutable after insert. Custom aliases are out of this lock.

## Diagram

```
TODO
```

## API

| Method | Path | Result |
| --- | --- | --- |
| POST | `/api/v1/data/shorten` | 201 metadata. Body `{"longURL": "<string>"}`. |
| GET | `/api/v1/data/{shortCode}` | 200 metadata JSON. No redirect. Unknown code is 404. |
| GET | `/api/v1/short/{shortCode}` | **302 Found**. `Location` is the original long URL. Increments `hits`. |
| GET | `/health` | 200 `{"status":"ok"}`. |

Metadata fields: `code`, `shortURL`, `longURL`, `created_at`, `hits`.

`shortURL` is `{PUBLIC_BASE_URL or request base}/api/v1/short/{code}`.

Validation at the HTTP boundary (Pydantic, OpenAPI at `/docs`):

- `longURL` must be `http` or `https`, max 2048 characters
- bad body → 422
- unknown code → 404

Auto codes use `[0-9a-zA-Z]` only. Generation starts at length 6 and grows on collision up to 12.

## Storage

`LinkStore` is the persistence interface. Production uses `PostgresLinkStore` when `DATABASE_URL` is set (SQLAlchemy 2.x + psycopg). `code` is the primary key (unique).

Without `DATABASE_URL` the process uses `MemoryLinkStore` so health and local API tests can run offline. CI sets `DATABASE_URL` and runs against Postgres.

## Scale (BOTE, not encoded in code)

Lucas planning numbers. The process does not preallocate 365B rows or hundreds of TB.

- 100M creates/day ≈ 100e6 / 86400 ≈ **1160 writes/s**
- Reads:writes ≈ 10:1 ⇒ about **12k redirects/s** at that create rate
- 10 years at 100M/day ≈ **365B records**
- ~100 byte average URL plus row overhead and indexes → **tens to hundreds of TB**

Implications:

- Managed Postgres for the durable unique `code` index
- App Platform multi-instance; uniqueness is the database constraint, not an in-process lock
- `GET /api/v1/short/{shortCode}` is the hot read path (lookup + `hits` increment)
- A 6-character base62 space is 62^6 ≈ 56.8B codes. Collision then lengthens. 7 characters is 62^7 ≈ 3.5T

## HA, uniqueness, idempotency

Target deploy (not provisioned here): App Platform, multiple app instances, Managed Postgres.

Concurrency control is the unique constraint on `code`. Two instances that roll the same random code: one insert wins, the other retries with a new code.

Create is not naturally idempotent. A client that retries after a lost 201 can insert a second code for the same long URL. On unknown outcome, GET `/api/v1/data/{shortCode}` if the client already saw a code; otherwise treat a retry as a new link.

`hits` increment is a single `UPDATE … SET hits = hits + 1` per redirect.

## Out of scope

DigitalOcean tokens, App Platform / Managed Postgres provisioning, update/delete, auth, custom aliases.
