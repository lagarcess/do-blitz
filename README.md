# do-blitz

FastAPI URL shortener. Create a short code, 302 to the original URL, read metadata. No update or delete.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | production / CI | Postgres URL. `postgres://`, `postgresql://`, or `postgresql+psycopg://`. |
| `PUBLIC_BASE_URL` | no | Prefix for `short_url`. Defaults to the incoming request base (`http://testserver` in tests). |
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

## API

```bash
curl -s localhost:8000/health
# {"status":"ok"}

curl -s -X POST localhost:8000/api/v1/links \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/page","alias":null}'
# 201 {"code":"…","short_url":"http://127.0.0.1:8000/…","long_url":"https://example.com/page","created_at":"…","hits":0}

curl -s -X POST localhost:8000/api/v1/links \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/page","alias":"MyLink1"}'

curl -sI localhost:8000/MyLink1
# 302 Location: https://example.com/page

curl -s localhost:8000/api/v1/links/MyLink1
```

Validation:

- URL must be `http` or `https` (else 422)
- Alias, if set: `[0-9a-zA-Z]`, 3–32 chars (else 422). Taken alias → 409
- Unknown code → 404

Auto codes are base62. Length starts at 6 and grows if the insert collides.

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
