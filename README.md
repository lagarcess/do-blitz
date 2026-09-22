# do-blitz

Scaffold for a FastAPI service (URL shortener domain TBD). **No shortener business logic yet** — health stub + package layout only.

Patterned after `hn-ingest` (`app` / `config` / `models` / `store`).

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 -m uvicorn do_blitz.app:app --host 0.0.0.0 --port 8000
curl -s localhost:8000/health
```

## Test

```bash
python3 -m pytest -q
```

## Docker

```bash
docker build -t do-blitz .
docker run --rm -p 8000:8000 do-blitz
```

## Out of scope (this scaffold)

DigitalOcean deploy, DO tokens, managed DB provision, shortener create/resolve logic.
