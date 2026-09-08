from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.config import Settings, get_settings
from app.constants import (
    CONSULTATION_DOCUMENTS_FILENAME,
    CONSULTATION_JSON_INDENT,
    CONSULTATION_META_FILENAME,
    CONSULTATION_NOT_FOUND_MESSAGE,
    CONSULTATION_TRANSCRIPT_FILENAME,
    EMPTY_AUDIO_MESSAGE,
    EXTRACT_NOT_READY_MESSAGE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    ConsultationStatus,
)
from app.consultation.schemas import (
    ConsultationAccepted,
    ConsultationMeta,
    ConsultationRead,
)
from app.exceptions import (
    AnthropicClientError,
    ConsultationNotFoundError,
    EmptyAudioError,
    ExtractNotReadyError,
    PyannoteClientError,
)
from app.extraction.schemas import ConsultationDocuments
from app.extraction.service import ExtractionService
from app.transcription.schemas import TranscribeAccepted
from app.transcription.service import TranscriptionService

logger = logging.getLogger(__name__)


class TranscriptionRunner(Protocol):
    async def start_transcription(self, content: bytes) -> TranscribeAccepted: ...

    async def wait_and_format(self, job_id: str) -> str: ...


class ExtractionRunner(Protocol):
    async def extract(self, transcript: str) -> ConsultationDocuments: ...


class ConsultationService:
    def __init__(
        self,
        settings: Settings | None = None,
        transcription_service: TranscriptionRunner | None = None,
        extraction_service: ExtractionRunner | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._transcription_service = transcription_service or TranscriptionService(
            settings=self._settings
        )
        self._extraction_service = extraction_service or ExtractionService(
            settings=self._settings
        )

    async def start(self, content: bytes) -> ConsultationAccepted:
        if not content:
            raise EmptyAudioError(EMPTY_AUDIO_MESSAGE)
        consultation_id = str(uuid4())
        now = datetime.now(UTC)
        self._consultation_dir(consultation_id).mkdir(parents=True, exist_ok=True)
        meta = ConsultationMeta(
            id=consultation_id,
            status=ConsultationStatus.TRANSCRIBING,
            created_at=now,
            updated_at=now,
        )
        self._write_meta(meta)
        try:
            accepted = await self._transcription_service.start_transcription(content)
        except (EmptyAudioError, PyannoteClientError):
            self._fail(consultation_id)
            raise
        self._write_meta(
            meta.model_copy(
                update={
                    "pyannote_job_id": accepted.job_id,
                    "updated_at": datetime.now(UTC),
                }
            )
        )
        return ConsultationAccepted(
            id=consultation_id,
            status=ConsultationStatus.TRANSCRIBING,
        )

    async def run_pipeline(self, consultation_id: str) -> None:
        meta = self._read_meta(consultation_id)
        if meta.pyannote_job_id is None:
            logger.error(
                "consultation transcription failed consultation_id=%s detail=%s",
                consultation_id,
                "missing pyannote_job_id",
            )
            self._fail(consultation_id)
            return
        try:
            transcript = await self._transcription_service.wait_and_format(
                meta.pyannote_job_id
            )
        except PyannoteClientError as exc:
            logger.error(
                "consultation transcription failed consultation_id=%s detail=%s",
                consultation_id,
                exc.message,
            )
            self._fail(consultation_id)
            return
        self._transcript_path(consultation_id).write_text(transcript, encoding="utf-8")
        self._write_meta(
            meta.model_copy(
                update={
                    "status": ConsultationStatus.EXTRACTING,
                    "error": None,
                    "updated_at": datetime.now(UTC),
                }
            )
        )
        await self.run_extract(consultation_id)

    async def start_extract(self, consultation_id: str) -> ConsultationAccepted:
        meta = self._read_meta(consultation_id)
        if (
            meta.status == ConsultationStatus.TRANSCRIBING
            or not self._transcript_path(consultation_id).is_file()
        ):
            raise ExtractNotReadyError(EXTRACT_NOT_READY_MESSAGE)
        self._write_meta(
            meta.model_copy(
                update={
                    "status": ConsultationStatus.EXTRACTING,
                    "error": None,
                    "updated_at": datetime.now(UTC),
                }
            )
        )
        return ConsultationAccepted(
            id=consultation_id,
            status=ConsultationStatus.EXTRACTING,
        )

    async def run_extract(self, consultation_id: str) -> None:
        transcript = self._transcript_path(consultation_id).read_text(encoding="utf-8")
        try:
            documents = await self._extraction_service.extract(transcript)
        except AnthropicClientError as exc:
            logger.error(
                "consultation extraction failed consultation_id=%s detail=%s",
                consultation_id,
                exc.message,
            )
            self._fail(consultation_id)
            return
        self._documents_path(consultation_id).write_text(
            documents.model_dump_json(indent=CONSULTATION_JSON_INDENT),
            encoding="utf-8",
        )
        meta = self._read_meta(consultation_id)
        self._write_meta(
            meta.model_copy(
                update={
                    "status": ConsultationStatus.SUCCEEDED,
                    "error": None,
                    "updated_at": datetime.now(UTC),
                }
            )
        )

    def get(self, consultation_id: str) -> ConsultationRead:
        meta = self._read_meta(consultation_id)
        documents = None
        if meta.status == ConsultationStatus.SUCCEEDED:
            documents = self._load_documents(consultation_id)
        return ConsultationRead(
            id=meta.id,
            status=meta.status,
            documents=documents,
            error=meta.error,
        )

    def _consultation_dir(self, consultation_id: str) -> Path:
        return self._settings.consultation_output_dir / consultation_id

    def _meta_path(self, consultation_id: str) -> Path:
        return self._consultation_dir(consultation_id) / CONSULTATION_META_FILENAME

    def _transcript_path(self, consultation_id: str) -> Path:
        return (
            self._consultation_dir(consultation_id) / CONSULTATION_TRANSCRIPT_FILENAME
        )

    def _documents_path(self, consultation_id: str) -> Path:
        return self._consultation_dir(consultation_id) / CONSULTATION_DOCUMENTS_FILENAME

    def _write_meta(self, meta: ConsultationMeta) -> None:
        self._meta_path(meta.id).write_text(
            meta.model_dump_json(indent=CONSULTATION_JSON_INDENT),
            encoding="utf-8",
        )

    def _read_meta(self, consultation_id: str) -> ConsultationMeta:
        path = self._meta_path(consultation_id)
        if not path.is_file():
            raise ConsultationNotFoundError(CONSULTATION_NOT_FOUND_MESSAGE)
        return ConsultationMeta.model_validate_json(path.read_text(encoding="utf-8"))

    def _load_documents(self, consultation_id: str) -> ConsultationDocuments | None:
        path = self._documents_path(consultation_id)
        if not path.is_file():
            return None
        return ConsultationDocuments.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def _fail(self, consultation_id: str) -> None:
        meta = self._read_meta(consultation_id)
        self._write_meta(
            meta.model_copy(
                update={
                    "status": ConsultationStatus.FAILED,
                    "error": INTERNAL_SERVER_ERROR_MESSAGE,
                    "updated_at": datetime.now(UTC),
                }
            )
        )
