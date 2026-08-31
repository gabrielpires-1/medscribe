# medscribe

FastAPI service for medical scribing.

## Setup

```bash
uv sync
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

## Health

`GET /health` returns `{"status": "ok"}`.
