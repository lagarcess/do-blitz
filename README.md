# do-blitz

FastAPI URL shortener. Mint a short code (random base62 or optional alias), 302 to the long URL, read metadata. Links are immutable after create — no update or delete.

Human-readable API docs: **`/redoc`** (primary). Swagger UI / try-it-out: `/docs` (secondary). Minimal shorten UI: `/`.

## Demo Kit

Live App Platform:

| | |
| --- | --- |
| UI | https://do-blitz-9tovc.ondigitalocean.app/ |
| ReDoc | https://do-blitz-9tovc.ondigitalocean.app/redoc |
| Swagger | https://do-blitz-9tovc.ondigitalocean.app/docs |
| Health | https://do-blitz-9tovc.ondigitalocean.app/health |
| Repo | https://github.com/lagarcess/do-blitz |

Walkthrough: open the UI → paste a `longURL` (optional alias) → copy `shortURL` → open it (**302**) → `GET /api/v1/data/{code}` shows `hits` / `last_accessed_at`. Or curl (GET, not HEAD) that prints **302** + redirect URL:

```bash
curl -sS -X POST https://do-blitz-9tovc.ondigitalocean.app/api/v1/data/shorten \
  -H 'content-type: application/json' \
  -d '{"longURL":"https://example.com/page"}'
# then, with the returned code:
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  https://do-blitz-9tovc.ondigitalocean.app/api/v1/short/<code>
# expect: 302 https://example.com/page
```

Local OrbStack steps stay under **Local run (OrbStack)** below.

## Architecture

Create and redirect share a load balancer and app instances. Postgres is the durable store. Cache (Redis when `REDIS_URL` is set, else process-local) is on the redirect path only — create never writes it.

```mermaid
flowchart TD
  subgraph Create["Create POST /api/v1/data/shorten"]
    C1[Client] --> CLB[Load balancer] --> CApp[App]
    CApp -->|rate limit deny| C429[429]
    CApp -->|alias or mint → INSERT| CPG[(Postgres)]
    CPG --> CApp
    CApp -->|ok| C201[201]
    CApp -->|alias taken| C409[409]
  end

  subgraph Redirect["Redirect GET /api/v1/short/{code}"]
    R1[Client] --> RLB[Load balancer] --> RApp[App]
    RApp --> RCache[(Cache Redis when configured)]
    RCache -->|hit or after DB hit| RUpd[Postgres UPDATE hits + last_accessed_at]
    RCache -->|miss| RPG[(Postgres SELECT)]
    RPG -->|miss| R404[404]
    RPG -->|hit: fill cache| RUpd
    RUpd --> R302[302 Location]
  end
```

Metadata `GET /api/v1/data/{code}` is Postgres only (no cache, no hit increment). Sequence detail, rate-limit / 409 / 404 branches: [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## API

| Method | Path | Result |
| --- | --- | --- |
| `POST` | `/api/v1/data/shorten` | `201` metadata. Body `{"longURL":"<url>","alias":"<optional>"}`. |
| `GET` | `/api/v1/data/{code}` | `200` metadata JSON (no redirect). |
| `GET` | `/api/v1/short/{code}` | **302 Found** to the long URL; increments `hit_count` and sets `last_accessed_at`. |
| `GET` | `/health` | `200` after a store ping. |
| `GET` | `/` | Demo UI (static). |

Metadata fields: `code`, `shortURL`, `longURL`, `created_at`, `hits`, `last_accessed_at`.

Validation: `longURL` must be `http`/`https` (max 2048). Optional `alias` is base62 `[0-9a-zA-Z]`, length 3–32, not reserved (`api`, `health`, `docs`, `short`, `data`, `v1`). Bad input → `422`. Taken alias → `409`. Unknown code → `404`. Shorten rate limit exceeded → `429`. Rate limit identity is the first `X-Forwarded-For` hop (else the direct client); spoofable unless App Platform / the LB sanitizes that header.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | **yes** for the running service | Postgres URL (`postgres://`, `postgresql://`, or `postgresql+psycopg://`). The process fails fast without it (no silent in-memory store in production). |
| `REDIS_URL` | no | Shared redirect cache + shorten rate limiter. Unset → process-local memory. |
| `RATE_LIMIT_SHORTEN_PER_MIN` | no | Per-IP cap on `POST /api/v1/data/shorten` per 60s window (default `60`; `0` disables). |
| `PUBLIC_BASE_URL` | no | Prefix for `shortURL` (defaults to the request base URL). |
| `PORT` | no | Listen port (default `8000`). Honored by the Dockerfile `CMD` (`${PORT:-8000}`). App Platform should set the component HTTP port to match (commonly `8000`). |
| `LOG_LEVEL` | no | Process log level (default `info`). Applied via `logging.basicConfig` at app startup. |
| `TEST_DATABASE_URL` | pytest only | Postgres URL pytest may wipe. Prefer this over `DATABASE_URL` for local/CI tests. |
| `ALLOW_TEST_DB_WIPE` | pytest only | Set to `1` only with a dedicated test DB name (`_test`) if you must reuse `DATABASE_URL` for pytest. Never enable against App Platform prod. |

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
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' localhost:8000/api/v1/short/promo1
# expect: 302 https://example.com/page
open http://localhost:8000/
```

## Tests

```bash
python3 -m pip install -r requirements.txt
# memory store (default — safe; does not wipe any DATABASE_URL)
python3 -m pytest -q

# Postgres integration (OrbStack). Use a dedicated test database only:
export TEST_DATABASE_URL=postgresql+psycopg://do_blitz:do_blitz@localhost:5432/do_blitz_test
python3 -m pytest -q
```

Pytest wipes only `TEST_DATABASE_URL`, or `DATABASE_URL` when `ALLOW_TEST_DB_WIPE=1` and the URL looks like a test DB (`_test`). Never point pytest at the App Platform production database. CI sets `TEST_DATABASE_URL` against an ephemeral Postgres service.

## Deploy shape (DigitalOcean)

Target: **App Platform** (stateless app containers) + **Managed Postgres** (+ optional Valkey/Redis for cache and rate limits). Set `DATABASE_URL` (and optionally `REDIS_URL`, `PUBLIC_BASE_URL`, rate-limit env) on the app. The `Dockerfile` in this repo is the **App Platform build artifact** — not the local development story.

App-tier HA needs ≥2 instances, but `basic-xxs`/`basic-xs` are capped at one instance — see the App Platform size vs HA note in [`ARCHITECTURE.md`](./ARCHITECTURE.md). This deploy stayed 1× `basic-xxs` for cost; Postgres standby covers data-plane durability. Capacity BOTE and other decision trades live in the same doc.

## Out of scope here

Provisioning DigitalOcean resources, Managed Redis, auth, update/delete of links, and click-history analytics beyond `hits` + `last_accessed_at`.
