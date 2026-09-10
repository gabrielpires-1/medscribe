# ADR 0002: Consultation pipeline — transcribe then extract

- **Status:** accepted
- **Date:** 2026-09-07
- **Supersedes:** public `POST /transcribe` contract in [ADR 0001](0001-transcribe-endpoint.md)

## Context

Medscribe must turn a consultation recording into reviewable clinical drafts (SOAP note, prescription, exam orders). Transcription is an implementation detail: the frontend only uploads audio, polls one consultation id, and reviews drafts. The diarized transcript must not leave the server.

Constraints and goals:

- One public aggregate (consultation), not a transcribe job plus a later extract call the client has to chain.
- Backend orchestrates pyannote.ai transcription and Claude structured extraction.
- Status is pollable; extract can be retried after a transcript exists.
- Failures stay user-safe on GET; operator detail stays in logs (same split as ADR 0001).
- Stay testable: injectable clients, no FastAPI types in services, fakes only in tests.

## Decision

### Public contract

| Method | Path | Success | Body |
|--------|------|---------|------|
| POST | `/consultations` | 202 | `{ "id", "status": "transcribing" }` |
| GET | `/consultations/{id}` | 200 | `{ "id", "status", "documents", "error" }` |
| POST | `/consultations/{id}/extract` | 202 | `{ "id", "status": "extracting" }` |

`id` is a medscribe UUID. The pyannote `job_id` is stored in `meta.json` only.

`documents` is `null` until extraction succeeds. GET **does not** return the transcript.

Statuses: `transcribing` → `extracting` → `succeeded` | `failed`.

| HTTP status | When |
|-------------|------|
| 202 | Create accepted (pipeline scheduled) or extract retry accepted |
| 400 | Empty audio file |
| 404 | Unknown consultation id |
| 409 | Extract retry while still transcribing, or when `transcript.txt` is missing |
| 502 | Upstream pyannote/Anthropic on the **start** path |
| 504 | Timeout on start-phase wait only |

### Orchestration

`ConsultationService.start` rejects empty audio, mints the id, writes `meta.json` (`transcribing`), starts pyannote upload+job creation, and returns 202. The route schedules `run_pipeline` via FastAPI `BackgroundTasks`.

`run_pipeline`:

1. `TranscriptionService.wait_and_format` → write `transcript.txt`, set `extracting`. On pyannote failure, timeout, or empty turns: status `failed`, `meta.error` = `INTERNAL_SERVER_ERROR_MESSAGE`, log operator detail. Do not call Claude.
2. `ExtractionService.extract` → write `documents.json`, status `succeeded`, clear error.
3. On Anthropic/validation failure: status `failed`, **keep** `transcript.txt`, user-safe error (retry is possible).

`POST /consultations/{id}/extract` only retries extraction. It requires `transcript.txt` and status other than `transcribing`, sets `extracting`, and schedules `run_extract`.

```
Client                medscribe                    pyannote.ai / Claude
  |  POST /consultations   |                              |
  | ---------------------> |  upload + create diarize job |
  |                        | ---------------------------> |
  |  202 { id, transcribing} |                            |
  | <--------------------- |                              |
  |                        |  [background] wait + format  |
  |                        | ---------------------------> |
  |                        |  write transcript.txt        |
  |                        |  messages.parse (Claude)     |
  |                        | ---------------------------> |
  |                        |  write documents.json        |
  |  GET /consultations/id |                              |
  | ---------------------> |                              |
  |  status + documents    |                              |
  | <--------------------- |                              |
```

### Storage

```
data/consultations/{consultation_id}/
  meta.json         # id, status, pyannote_job_id, error, timestamps — source of GET status
  transcript.txt    # LLM-ready turns; never served
  documents.json    # validated ConsultationDocuments
```

Configurable via `MEDSCRIBE_CONSULTATION_OUTPUT_DIR` (default `data/consultations`). Failed pyannote jobs do **not** write `"Internal Server Error"` into `transcript.txt`; that message lives in `meta.error`. Job ids and upstream payloads stay in logs.

### Extraction (official Anthropic SDK)

Claude is called through the official `anthropic` package (`AsyncAnthropic`), not httpx2. Pyannote remains on httpx2.

`AnthropicClient` is an injectable wrapper. Extraction never constructs the SDK itself.

Structured output uses `messages.parse(..., output_format=ConsultationDocuments)`. The SDK derives JSON Schema from the Pydantic model and returns typed `parsed_output`. We do not hand-roll `output_config`, `json.loads`, or a second `model_validate` unless `parsed_output` is missing or invalid (then raise `AnthropicClientError`).

SDK failures (`APIError`, timeout, refusal `stop_reason`, missing `parsed_output`) map to `AnthropicClientError`.

One Claude call returns SOAP + prescription + exam orders. English JSON keys; clinical content in Portuguese. Missing data is empty string or empty list — never invented facts. Speakers remain unlabeled `SPEAKER_XX`. Output is a draft for human review.

### Layered architecture

| Layer | Module | Responsibility |
|-------|--------|----------------|
| HTTP aggregate | `app/consultation/route.py` | Parse upload, map exceptions to HTTP, schedule background tasks |
| Orchestration | `app/consultation/service.py` | Create record, run pipeline, retry extract, read status; owns disk |
| HTTP/JSON schemas | `app/consultation/schemas.py` | Accepted / Read / filesystem meta |
| Transcription (internal) | `app/transcription/service.py` | Upload, create job, wait, format turns. No public route. |
| Extraction | `app/extraction/service.py` | Prompt + `AnthropicClient.parse` → `ConsultationDocuments` |
| Documents / prompt | `app/extraction/schemas.py`, `app/extraction/prompts.py` | Pydantic documents; PT-BR system prompt |
| Anthropic I/O | `app/clients/anthropic_client.py` | Thin `AsyncAnthropic` wrapper; no business rules |
| Pyannote I/O | `app/clients/pyannote_client.py` | Unchanged httpx2 client |

Routes never call pyannote or Anthropic directly. Services never import FastAPI request/response types.

### Testing approach

- Route tests mock `ConsultationService`; assert status codes, response schema, 409 retry, 400 empty file, 502 mapping.
- Service tests use `tmp_path` and mocked transcription/extraction: pipeline success, pyannote fail does not call Claude, extract fail keeps transcript, retry.
- Anthropic client tests mock `AsyncAnthropic` / `messages.parse` (not httpx). Extraction tests map client errors.
- Transcription tests cover `wait_and_format`. No real network, Anthropic, pyannote, or clinical data.

## Consequences

### Positive

- Frontend has a single pollable aggregate; transcript stays on the server.
- Extract retry does not re-run pyannote when the transcript already exists.
- Structured outputs stay typed via the official SDK.
- User-facing GET errors are safe; technical detail stays in logs.

### Negative / trade-offs

- **No delivery guarantee for background tasks.** If the process exits before `run_pipeline` / `run_extract` completes, status may stick at `transcribing` or `extracting`. Acceptable for MVP; a durable queue would be needed for production hardening.
- **Local filesystem storage.** Not suitable for multi-instance deployment without shared storage.
- **Speaker roles unknown.** Prompts treat `SPEAKER_XX` as opaque labels.
- **Start-path 502 can leave a failed consultation directory** whose id was never returned to the client.

## Related files

- `app/consultation/route.py`, `app/consultation/service.py`, `app/consultation/schemas.py`
- `app/transcription/service.py`
- `app/extraction/service.py`, `app/extraction/schemas.py`, `app/extraction/prompts.py`
- `app/clients/anthropic_client.py`
- `docs/adr/0001-transcribe-endpoint.md` — superseded public contract; pyannote/format decisions still apply
