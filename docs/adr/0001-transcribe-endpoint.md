# ADR 0001: POST /transcribe — async transcription via pyannote.ai

- **Status:** superseded by [ADR 0002](0002-consultation-pipeline.md) for the public HTTP contract
- **Date:** 2026-09-07

## Supersession

ADR 0002 replaces the public `POST /transcribe` contract with a consultation aggregate (`POST /GET /consultations`, extract retry). Transcription is an internal step: the client never receives a pyannote `job_id` or the transcript.

The following decisions **remain in effect** for that internal step:

- pyannote.ai as the diarization/transcription provider
- Turn-level plain-text format (`[SPEAKER_XX] …`)
- Layered architecture (HTTP / service / client / schemas)
- User-safe error vs operator logs split (`INTERNAL_SERVER_ERROR_MESSAGE` to the client; job detail in logs)
- FastAPI `BackgroundTasks` as the MVP async model (no delivery guarantee)

Do not use this ADR as the source of truth for HTTP paths, response bodies, or on-disk layout. See ADR 0002.


## Context

Medscribe needs to accept audio recordings of medical conversations, run speaker diarization and transcription, and produce a text artifact suitable for downstream LLM processing (structured note extraction, summaries, etc.).

Constraints and goals:

- Transcription is slow (seconds to minutes); the HTTP caller must not block until pyannote.ai finishes.
- The service must stay testable: external I/O isolated behind injectable clients, business logic outside route handlers.
- Output should minimize token usage for later LLM calls while preserving speaker attribution.
- Failures must be observable for operators without exposing internal details to end users reading saved files.

## Decision

### Endpoint contract

`POST /transcribe` accepts a multipart audio upload (`file`) and returns **202 Accepted** immediately with:

```json
{ "job_id": "<pyannote-job-id>", "status": "created" }
```

The caller uses `job_id` to locate the persisted result at `data/transcriptions/{job_id}.txt` (configurable via `MEDSCRIBE_TRANSCRIPTION_OUTPUT_DIR`).

| HTTP status | When |
|-------------|------|
| 202 | Job created; background persistence scheduled |
| 400 | Empty audio file |
| 502 | pyannote.ai request or upload failure |
| 504 | pyannote job polling timed out during **start** phase (not background) |

There is no polling or status endpoint yet; the client is expected to read the `.txt` file once processing completes.

### Async processing model

The route handler performs only the **fast path**:

1. Read uploaded bytes.
2. Upload audio to pyannote.ai (`create_media_input` → presigned PUT).
3. Create a diarize+transcription job (`POST /v1/diarize` with `transcription: true`, model `precision-2`).

A FastAPI `BackgroundTasks` callback runs `persist_job_result(job_id)` after the 202 response is sent. That task:

1. Polls `GET /v1/jobs/{job_id}` until success, failure, cancel, or timeout.
2. Writes the result to disk as plain text.

Polling interval and timeout are configurable (`MEDSCRIBE_PYANNOTE_POLL_INTERVAL_SECONDS`, default 10s; `MEDSCRIBE_PYANNOTE_POLL_TIMEOUT_SECONDS`, default 600s).

```
Client                medscribe                 pyannote.ai
  |  POST /transcribe     |                         |
  | --------------------> |  upload + create job    |
  |                       | ----------------------> |
  |  202 { job_id }       |                         |
  | <-------------------- |                         |
  |                       |  [background] poll job  |
  |                       | ----------------------> |
  |                       |  write {job_id}.txt     |
  |  read .txt file       |                         |
  | --------------------> |                         |
```

### Layered architecture

| Layer | Module | Responsibility |
|-------|--------|----------------|
| HTTP | `app/transcription/route.py` | Parse upload, map exceptions to HTTP, schedule background task |
| Business | `app/transcription/service.py` | Orchestrate upload, job creation, polling, formatting, persistence |
| External API | `app/clients/pyannote_client.py` | httpx calls to pyannote.ai; no business rules |
| Schemas | `app/transcription/schemas.py`, `app/clients/pyannote_schemas.py` | Pydantic request/response and pyannote payload models |
| Config | `app/config.py` | Settings from env (`MEDSCRIBE_*` prefix) |
| Errors | `app/exceptions.py` | Typed domain errors translated in the route |

Routes never call pyannote directly; services never import FastAPI request/response types.

### Transcription provider

pyannote.ai is the sole upstream for diarization and transcription. Authentication uses `MEDSCRIBE_PYANNOTE_API_KEY` (Bearer token). Base URL defaults to `https://api.pyannote.ai`.

Audio is referenced internally as `media://{uuid}` after upload; the diarize job is created against that URL.

### Output format (LLM-oriented plain text)

We persist **only** `turnLevelTranscription` from the pyannote job output — not the full JSON body, not word-level segments, not raw diarization intervals.

Each turn becomes one line:

```
[SPEAKER_00] First utterance text.
[SPEAKER_01] Reply text.
```

Rationale:

- Turn-level text is ~10× smaller than word-level JSON with negligible loss for semantic extraction.
- Plain text with speaker prefixes is token-efficient and matches common LLM dialogue formats.
- Speaker labels remain pyannote identifiers (`SPEAKER_00`, `SPEAKER_01`); **clinician/patient role mapping is deferred** until a reliable heuristic or user input exists.

Files are written as `{job_id}.txt` under the configured output directory.

### Error handling and observability

Two audiences, two surfaces:

**User-facing file** (what someone opening `{job_id}.txt` sees on failure):

```
Internal Server Error
2026-09-07T14:33:04.358000+00:00
```

No `job_id`, job status, pyannote error payload, or stack traces in the file.

**Server logs** (operators):

```
ERROR transcription persist failed job_id=... status=... detail=... occurred_at=...
```

The timestamp in the file matches `occurred_at` in logs so incidents can be correlated by time.

Failed pyannote jobs (`FAILED`, `CANCELED`) and jobs with missing/empty `turnLevelTranscription` follow the error path. `PyannoteJobFailedError` carries the terminal job when available so its output can still be inspected before writing the user-facing file.

### Testing approach

- Route tests mock `TranscriptionService`; assert status codes, response schema, and that `persist_job_result` is scheduled.
- Service tests mock `PyannoteClient`; assert `.txt` content for success and failure paths, plus log output via `caplog`.
- Client tests mock httpx; no real network or audio files in tests.

## Consequences

### Positive

- Fast API response; long-running work does not hold connections open.
- Clear separation of concerns; each layer has a single test target.
- Plain-text output is ready for LLM prompts without further parsing.
- User-facing errors are safe; technical detail stays in logs.

### Negative / trade-offs

- **No delivery guarantee for background tasks.** If the process exits before `persist_job_result` completes, the `.txt` file may never appear. Acceptable for now; a durable queue (Celery, ARQ, etc.) would be needed for production hardening.
- **No status API.** Clients must poll the filesystem or wait out-of-band; there is no `GET /transcribe/{job_id}` yet.
- **Local filesystem storage.** Not suitable for multi-instance deployment without shared storage or object store migration.
- **Speaker roles unknown.** Downstream LLM prompts must treat `SPEAKER_XX` as opaque labels until mapping is implemented.
- **Background timeout failures** are not surfaced to the HTTP caller; they appear only as error `.txt` files and log entries.

## Related files

- `app/transcription/route.py` — HTTP entrypoint
- `app/transcription/service.py` — orchestration and formatting
- `app/clients/pyannote_client.py` — pyannote.ai integration
- `app/config.py` — environment configuration
- `tests/transcription/test_route.py`, `tests/transcription/test_service.py` — tests
