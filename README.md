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

## Frontend

The consultation UI is a Next.js app in `frontend/`. With the API running:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Recordings used for audio-quality review are written to `frontend/recordings/` during `next dev`.
