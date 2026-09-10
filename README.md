# medscribe

Open-source MVP that turns medical consultation recordings into **editable drafts** of a medical record (SOAP), prescription, and lab/imaging orders. The UI is in Brazilian Portuguese.

Pipeline: **audio → diarized transcription (pyannote.ai) → structured extraction (Claude) → human review in the browser**.

> **Disclaimer:** this software produces drafts for review — it does not replace clinical judgment. Do not use with real patient data without assessing privacy law (e.g. LGPD), consent, and agreements with external providers.

## Prerequisites

| Tool | Minimum version | Purpose |
|------|-----------------|---------|
| [Python](https://www.python.org/) | 3.12+ | API (FastAPI) |
| [uv](https://docs.astral.sh/uv/) | recent | Python dependencies |
| [Node.js](https://nodejs.org/) | 20+ | Next.js frontend |
| npm | (bundled with Node) | frontend |

## API keys (required)

The backend **will not start** without both keys below. Create accounts with the providers and generate API tokens.

### 1. pyannote.ai — transcription and diarization

- **Website:** [https://pyannote.ai](https://pyannote.ai)
- **Variable:** `MEDSCRIBE_PYANNOTE_API_KEY`
- **Role:** sends consultation audio, separates speakers (`SPEAKER_00`, `SPEAKER_01`, …), and returns turn-by-turn transcription.
- **Docs:** [https://docs.pyannote.ai](https://docs.pyannote.ai)

### 2. Anthropic — clinical document extraction

- **Website:** [https://console.anthropic.com](https://console.anthropic.com)
- **Variable:** `MEDSCRIBE_ANTHROPIC_API_KEY`
- **Role:** reads the transcript and generates structured JSON (SOAP, prescription, exam orders) via Claude with typed output.
- **Default model:** `claude-sonnet-4-5` (`MEDSCRIBE_ANTHROPIC_MODEL`)
- **Docs:** [https://docs.anthropic.com](https://docs.anthropic.com)

**Cost:** both services are pay-as-you-go. Check pricing before running long or high-volume consultations.

## Setup

From the repository root:

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
MEDSCRIBE_PYANNOTE_API_KEY=your-pyannote-key
MEDSCRIBE_ANTHROPIC_API_KEY=your-anthropic-key
MEDSCRIBE_ANTHROPIC_MODEL=claude-sonnet-4-5
MEDSCRIBE_CORS_ORIGINS=["http://localhost:3000"]
```

Install Python dependencies:

```bash
uv sync
```

Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

### Environment variables (reference)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEDSCRIBE_PYANNOTE_API_KEY` | yes | — | pyannote.ai Bearer token |
| `MEDSCRIBE_ANTHROPIC_API_KEY` | yes | — | Anthropic API key |
| `MEDSCRIBE_ANTHROPIC_MODEL` | no | `claude-sonnet-4-5` | Claude model for extraction |
| `MEDSCRIBE_ANTHROPIC_MAX_TOKENS` | no | `8192` | Max tokens in the response |
| `MEDSCRIBE_ANTHROPIC_BASE_URL` | no | `https://api.anthropic.com` | Anthropic API base URL |
| `MEDSCRIBE_PYANNOTE_BASE_URL` | no | `https://api.pyannote.ai` | pyannote.ai base URL |
| `MEDSCRIBE_PYANNOTE_POLL_INTERVAL_SECONDS` | no | `10` | pyannote job poll interval |
| `MEDSCRIBE_PYANNOTE_POLL_TIMEOUT_SECONDS` | no | `600` | pyannote job total timeout |
| `MEDSCRIBE_CONSULTATION_OUTPUT_DIR` | no | `data/consultations` | Directory for persisted consultations |
| `MEDSCRIBE_CORS_ORIGINS` | no | `["http://localhost:3000"]` | CORS allowed origins (JSON array) |

Frontend (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDSCRIBE_API_URL` | `http://localhost:8000` | API URL for the Next.js proxy |

## Run

Use **two terminals**.

**Terminal 1 — API:**

```bash
uv run uvicorn app.main:app --reload
```

API at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Using the UI

1. Click **Gravar consulta** (Record consultation) and allow microphone access.
2. Stop recording when the consultation ends (or upload an audio file if that option is enabled).
3. Wait for processing: transcription → document extraction.
4. Review and edit drafts for **Medical record (SOAP)**, **Prescription**, and **Exam orders**.
5. Fill in the header (patient, physician, etc.) and use **Print** when ready.

In development (`npm run dev`), a copy of the audio may be saved under `frontend/recordings/` for quality review — that directory is in `.gitignore`.

## How it works

### Pipeline

```
Browser            medscribe (API)              External services
    |                    |                              |
    | POST /consultations|                              |
    | (audio upload)     | upload + diarize job         |
    | -----------------> | ---------------------------> | pyannote.ai
    | 202 { id }         |                              |
    |                    | [background] poll + format   |
    |                    | ---------------------------> | pyannote.ai
    |                    | write transcript.txt         |
    |                    | messages.parse (Claude)      |
    |                    | ---------------------------> | Anthropic
    |                    | write documents.json         |
    | GET /consultations/{id} (poll)                    |
    | -----------------> |                              |
    | status + drafts    |                              |
    | <----------------- |                              |
```

Consultation states: `transcribing` → `extracting` → `succeeded` | `failed`.

The **diarized transcript is not exposed** by the public API — it stays on disk on the server. The client receives status and, when ready, structured documents.

### Local storage

Each consultation creates a directory:

```
data/consultations/{consultation_id}/
  meta.json         # id, status, timestamps, error (if any)
  transcript.txt    # LLM-ready transcript (not served by the API)
  documents.json    # validated SOAP, prescription, and exam orders
```

The `data/` directory is in `.gitignore` — real consultation data must not be committed.

### Generated documents

| Document | Contents |
|----------|----------|
| Medical record | SOAP (subjective, objective, assessment, plan) |
| Prescription | medication list (name, dosage, route, frequency, duration, instructions) |
| Exam orders | order list (name, indication, instructions) |

The extraction prompt instructs the model **not to invent** clinical facts missing from the transcript and to treat speakers only as `SPEAKER_XX` (without assuming clinician vs. patient roles).

### HTTP API

| Method | Path | Success | Description |
|--------|------|---------|-------------|
| `GET` | `/health` | 200 | Health check (`{"status": "ok"}`) |
| `POST` | `/consultations` | 202 | Upload audio (`multipart/form-data`, field `file`) |
| `GET` | `/consultations/{id}` | 200 | Poll status and documents |
| `POST` | `/consultations/{id}/extract` | 202 | Retry extraction only (no re-transcription) |

Full contract: [docs/adr/0002-consultation-pipeline.md](docs/adr/0002-consultation-pipeline.md).

Example with `curl`:

```bash
curl -X POST http://localhost:8000/consultations \
  -F "file=@consultation.wav"

curl http://localhost:8000/consultations/{id}
```

## Third-party services and libraries

### External APIs

| Service | Role in medscribe |
|---------|-------------------|
| **[pyannote.ai](https://pyannote.ai)** | Audio upload, diarization, and transcription |
| **[Anthropic Claude](https://www.anthropic.com)** | Structured extraction of clinical drafts |

Using the software sends audio and transcript text to these providers under their privacy policies and terms of use.

### Backend (Python)

| Library | Role |
|---------|------|
| [FastAPI](https://fastapi.tiangolo.com/) | HTTP API, upload, background tasks |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | Official SDK — `messages.parse` with Pydantic output |
| [httpx2](https://pypi.org/project/httpx2/) | HTTP client for the pyannote.ai API |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Configuration via `.env` |

Dependency management: [uv](https://docs.astral.sh/uv/).

### Frontend (TypeScript)

| Library | Role |
|---------|------|
| [Next.js](https://nextjs.org/) | App Router, proxies `/consultations` to the API |
| [React](https://react.dev/) | Recording and draft review UI |

Browser APIs: `MediaRecorder` and `getUserMedia` for audio capture.

## Development

Python tests and quality gates:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pylint app tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## MVP limitations

- **No authentication** — any client that can reach the API can create consultations.
- **Background tasks** — if the API process exits mid-pipeline, status may stay stuck at `transcribing` or `extracting`.
- **Local disk** — no durable queue or shared storage across instances.
- **Drafts, not final records** — always require human review before any clinical use.

## Project layout

```
app/
  consultation/     # routes and consultation orchestration
  transcription/    # pyannote integration (internal, no public route)
  extraction/       # document schemas and prompts
  clients/          # pyannote and Anthropic wrappers
frontend/           # Next.js UI (pt-BR)
docs/adr/           # architecture decisions
tests/              # pytest (fake data, no network)
```

## License

See [LICENSE](LICENSE).
