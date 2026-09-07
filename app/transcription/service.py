from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.clients.pyannote_client import PyannoteClient
from app.clients.pyannote_schemas import DiarizationJob, TranscriptionSegment
from app.config import Settings, get_settings
from app.constants import INTERNAL_SERVER_ERROR_MESSAGE, TRANSCRIPTION_FILE_SUFFIX
from app.exceptions import EmptyAudioError, PyannoteJobFailedError
from app.transcription.schemas import TranscribeAccepted

logger = logging.getLogger(__name__)


def format_turn_level_transcript(segments: list[TranscriptionSegment]) -> str:
    return "\n".join(f"[{seg.speaker}] {seg.text}" for seg in segments)


def format_user_error(occurred_at: datetime) -> str:
    return f"{INTERNAL_SERVER_ERROR_MESSAGE}\n{occurred_at.isoformat()}"


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
            raise EmptyAudioError("audio file is empty")
        object_key = uuid4().hex
        media_url = await self._client.upload_audio(object_key, content)
        created = await self._client.create_diarize_job(media_url)
        return TranscribeAccepted(job_id=created.job_id, status=created.status)

    async def persist_job_result(self, job_id: str) -> None:
        try:
            job = await self._client.wait_for_job(job_id)
        except PyannoteJobFailedError as exc:
            if exc.job is None:
                raise
            job = exc.job
        self._write_job(job)

    def _write_job(self, job: DiarizationJob) -> None:
        output_dir = self._settings.transcription_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{job.job_id}{TRANSCRIPTION_FILE_SUFFIX}"

        turns = job.output.turn_level_transcription if job.output is not None else None
        if turns:
            path.write_text(format_turn_level_transcript(turns), encoding="utf-8")
            return

        occurred_at = job.updated_at or datetime.now(UTC)
        detail = job.output.error if job.output else None
        logger.error(
            "transcription persist failed job_id=%s status=%s detail=%s occurred_at=%s",
            job.job_id,
            job.status,
            detail,
            occurred_at.isoformat(),
        )
        path.write_text(format_user_error(occurred_at), encoding="utf-8")
