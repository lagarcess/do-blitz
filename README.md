# do-blitz

FastAPI URL shortener. Shorten a long URL, 302 to it, read metadata. No update or delete.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | production / CI | Postgres URL. `postgres://`, `postgresql://`, or `postgresql+psycopg://`. |
| `PUBLIC_BASE_URL` | no | Prefix for `shortURL`. Defaults to the incoming request base (`http://testserver` in tests). |
| `PORT` | no | Listen port (default `8000`). Used by operators; uvicorn still needs `--port`. |
| `LOG_LEVEL` | no | Default `info`. |

Without `DATABASE_URL` the app keeps links in memory (lost on restart). Use Postgres for anything you want to keep.

## Local Postgres (OrbStack or Docker)

```bash
docker run --name do-blitz-pg \
  -e POSTGRES_USER=do_blitz \
  -e POSTGRES_PASSWORD=do_blitz \
  -e POSTGRES_DB=do_blitz \
  -p 5432:5432 \
  postgres:16

export DATABASE_URL=postgresql+psycopg://do_blitz:do_blitz@localhost:5432/do_blitz
```

Tables are created on startup (`links`, unique `code`).

## Setup and run

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn do_blitz.app:app --host 0.0.0.0 --port 8000
```

OpenAPI: `http://localhost:8000/docs`.

## API

```bash
curl -s localhost:8000/health
# {"status":"ok"}

curl -s -X POST localhost:8000/api/v1/data/shorten \
  -H 'content-type: application/json' \
  -d '{"longURL":"https://example.com/page"}'
# 201 {"code":"CQfE0v","shortURL":"http://127.0.0.1:8000/api/v1/short/CQfE0v","longURL":"https://example.com/page","created_at":"…","hits":0}

curl -sI localhost:8000/api/v1/short/CQfE0v
# 302 Found
# Location: https://example.com/page

curl -s localhost:8000/api/v1/data/CQfE0v
# {"code":"CQfE0v","shortURL":"http://127.0.0.1:8000/api/v1/short/CQfE0v","longURL":"https://example.com/page","created_at":"…","hits":1}
```

Validation:

- `longURL` must be `http` or `https` and at most 2048 characters (else 422)
- Unknown code → 404

Auto codes are base62 `[0-9a-zA-Z]`. Length starts at 6 and grows if the insert collides.

## Tests

```bash
python3 -m pytest -q
```

With `DATABASE_URL` unset, API tests use the in-memory store. CI starts a Postgres service and sets `DATABASE_URL` so the same tests run against `PostgresLinkStore`.

```bash
export DATABASE_URL=postgresql+psycopg://do_blitz:do_blitz@localhost:5432/do_blitz
python3 -m pytest -q
```

## Docker

Needs a reachable Postgres (`DATABASE_URL`).

```bash
docker build -t do-blitz .
docker run --rm -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" do-blitz
```

## Out of scope

DigitalOcean deploy, DO tokens, and managed-DB provisioning. See `ARCHITECTURE.md` for HA and scale notes.
