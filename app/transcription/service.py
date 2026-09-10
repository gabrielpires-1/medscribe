from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.clients.pyannote_client import PyannoteClient
from app.clients.pyannote_schemas import DiarizationJob, TranscriptionSegment
from app.config import Settings, get_settings
from app.constants import EMPTY_AUDIO_MESSAGE
from app.exceptions import (
    EmptyAudioError,
    EmptyTranscriptError,
    PyannoteJobFailedError,
    PyannoteJobTimeoutError,
)
from app.transcription.schemas import TranscribeAccepted

logger = logging.getLogger(__name__)


def format_turn_level_transcript(segments: list[TranscriptionSegment]) -> str:
    return "\n".join(f"[{seg.speaker}] {seg.text}" for seg in segments)


def _log_wait_failure(job_id: str, job: DiarizationJob | None) -> None:
    occurred_at = datetime.now(UTC)
    status = None
    detail = None
    if job is not None:
        status = job.status
        if job.updated_at is not None:
            occurred_at = job.updated_at
        if job.output is not None:
            detail = job.output.error
    logger.error(
        "transcription wait failed job_id=%s status=%s detail=%s occurred_at=%s",
        job_id,
        status,
        detail,
        occurred_at.isoformat(),
    )


class TranscriptionService:
    def __init__(
        self,
        client: PyannoteClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or PyannoteClient(settings=self._settings)

    async def start_transcription(self, content: bytes) -> TranscribeAccepted:
        if not content:
            raise EmptyAudioError(EMPTY_AUDIO_MESSAGE)
        object_key = uuid4().hex
        media_url = await self._client.upload_audio(object_key, content)
        created = await self._client.create_diarize_job(media_url)
        return TranscribeAccepted(job_id=created.job_id, status=created.status)

    async def wait_and_format(self, job_id: str) -> str:
        try:
            job = await self._client.wait_for_job(job_id)
        except PyannoteJobTimeoutError:
            _log_wait_failure(job_id, None)
            raise
        except PyannoteJobFailedError as exc:
            _log_wait_failure(job_id, exc.job)
            raise
        turns = job.output.turn_level_transcription if job.output is not None else None
        if not turns:
            _log_wait_failure(job_id, job)
            raise EmptyTranscriptError(f"job {job_id} has no turn-level transcription")
        return format_turn_level_transcript(turns)
