# do-blitz

Production-shaped FastAPI URL shortener for a time-boxed interview build. Mint a short code (random base62 or optional alias), 302 to the long URL, read metadata. Links are immutable after create — no update or delete.

OpenAPI lives at `/docs`. A minimal shorten UI is served at `/`.

## API

| Method | Path | Result |
| --- | --- | --- |
| `POST` | `/api/v1/data/shorten` | `201` metadata. Body `{"longURL":"<url>","alias":"<optional>"}`. |
| `GET` | `/api/v1/data/{code}` | `200` metadata JSON (no redirect). |
| `GET` | `/api/v1/short/{code}` | **302 Found** to the long URL; increments `hit_count` and sets `last_accessed_at`. |
| `GET` | `/health` | `200` after a store ping. |
| `GET` | `/` | Demo UI (static). |

Metadata fields: `code`, `shortURL`, `longURL`, `created_at`, `hits`, `last_accessed_at`.

Validation: `longURL` must be `http`/`https` (max 2048). Optional `alias` is base62 `[0-9a-zA-Z]`, length 3–32, not reserved (`api`, `health`, `docs`, `short`, `data`, `v1`). Bad input → `422`. Taken alias → `409`. Unknown code → `404`. Shorten rate limit exceeded → `429`.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | **yes** for the running service | Postgres URL (`postgres://`, `postgresql://`, or `postgresql+psycopg://`). The process fails fast without it (no silent in-memory store in production). |
| `REDIS_URL` | no | Shared redirect cache + shorten rate limiter. Unset → process-local memory. |
| `RATE_LIMIT_SHORTEN_PER_MIN` | no | Per-IP cap on `POST /api/v1/data/shorten` per 60s window (default `60`; `0` disables). |
| `PUBLIC_BASE_URL` | no | Prefix for `shortURL` (defaults to the request base URL). |
| `PORT` | no | Operator listen port (default `8000`). |
| `LOG_LEVEL` | no | Default `info`. |

## Local run (OrbStack)

Team local path is **OrbStack**, not Docker Desktop. Create Postgres (and optional Redis/Valkey) in OrbStack, then:

```bash
export DATABASE_URL=postgresql+psycopg://do_blitz:do_blitz@localhost:5432/do_blitz
# optional: export REDIS_URL=redis://localhost:6379/0

python3 -m pip install -r requirements.txt
python3 -m uvicorn do_blitz.app:app --host 0.0.0.0 --port 8000
```

Tables are created on startup (`links`: `code`, `long_url`, `created_at`, `hit_count`, `last_accessed_at`).

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/api/v1/data/shorten \
  -H 'content-type: application/json' \
  -d '{"longURL":"https://example.com/page","alias":"promo1"}'
curl -sI localhost:8000/api/v1/short/promo1
open http://localhost:8000/
```

## Tests

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
```

Without `DATABASE_URL`, API tests inject an in-memory store via fixtures. CI starts Postgres and sets `DATABASE_URL` so the same suite exercises `PostgresLinkStore`.

## Deploy shape (DigitalOcean)

Target: **App Platform** (stateless app containers) + **Managed Postgres**. Set `DATABASE_URL` (and optionally `REDIS_URL`, `PUBLIC_BASE_URL`, rate-limit env) on the app. The `Dockerfile` in this repo is the **App Platform build artifact** — not the local development story.

HA notes, capacity BOTE, and decision trades: see [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## Out of scope here

Provisioning DigitalOcean resources, Managed Redis, auth, update/delete of links, and click-history analytics beyond `hits` + `last_accessed_at`.
