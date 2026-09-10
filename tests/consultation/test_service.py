import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from app.config import Settings
from app.constants import (
    CONSULTATION_JSON_INDENT,
    CONSULTATION_NOT_FOUND_MESSAGE,
    EXTRACT_NOT_READY_MESSAGE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    ConsultationStatus,
    JobStatus,
)
from app.consultation.service import ConsultationService
from app.exceptions import (
    AnthropicClientError,
    ConsultationNotFoundError,
    EmptyAudioError,
    ExtractNotReadyError,
    PyannoteClientError,
)
from app.transcription.schemas import TranscribeAccepted
from tests.fakes import fake_consultation_documents

CONSULTATION_ID = "00000000-0000-4000-8000-000000000001"
CONSULTATION_UUID = UUID(CONSULTATION_ID)
FAKE_TRANSCRIPT = "[SPEAKER_00] fake-turn-one\n[SPEAKER_01] fake-turn-two"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        pyannote_api_key="fake-api-key",
        anthropic_api_key="fake-anthropic-key",
        consultation_output_dir=tmp_path,
    )


def _service(
    tmp_path: Path,
    *,
    transcription_service: AsyncMock | None = None,
    extraction_service: AsyncMock | None = None,
) -> ConsultationService:
    return ConsultationService(
        settings=_settings(tmp_path),
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )


def _patch_uuid(mocker: MockerFixture) -> None:
    mocker.patch("app.consultation.service.uuid4", return_value=CONSULTATION_UUID)


def _meta(tmp_path: Path) -> dict[str, object]:
    path = tmp_path / CONSULTATION_ID / "meta.json"
    return json.loads(path.read_text(encoding="utf-8"))


async def test_start_rejects_empty_audio(tmp_path: Path) -> None:
    with pytest.raises(EmptyAudioError):
        await _service(tmp_path).start(b"")


async def test_run_pipeline_writes_transcript_and_documents(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _patch_uuid(mocker)
    transcription_service = AsyncMock()
    transcription_service.start_transcription = AsyncMock(
        return_value=TranscribeAccepted(job_id="job-0001", status=JobStatus.CREATED)
    )
    transcription_service.wait_and_format = AsyncMock(return_value=FAKE_TRANSCRIPT)
    extraction_service = AsyncMock()
    extraction_service.extract = AsyncMock(return_value=fake_consultation_documents())
    service = _service(
        tmp_path,
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )
    accepted = await service.start(b"fake-audio-bytes")
    await service.run_pipeline(accepted.id)

    consultation_dir = tmp_path / CONSULTATION_ID
    saved_transcript = (consultation_dir / "transcript.txt").read_text(encoding="utf-8")
    assert saved_transcript == FAKE_TRANSCRIPT
    documents = (consultation_dir / "documents.json").read_text(encoding="utf-8")
    assert "lorem-ipsum-subjetivo" in documents
    assert documents.startswith("{\n")
    assert f'\n{" " * CONSULTATION_JSON_INDENT}"medical_record"' in documents
    raw_meta = (consultation_dir / "meta.json").read_text(encoding="utf-8")
    assert raw_meta.startswith("{\n")
    assert f'\n{" " * CONSULTATION_JSON_INDENT}"id"' in raw_meta
    meta = _meta(tmp_path)
    assert meta["status"] == ConsultationStatus.SUCCEEDED
    assert meta["error"] is None
    assert meta["pyannote_job_id"] == "job-0001"
    extraction_service.extract.assert_awaited_once_with(FAKE_TRANSCRIPT)


async def test_pyannote_failure_does_not_call_claude(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _patch_uuid(mocker)
    transcription_service = AsyncMock()
    transcription_service.start_transcription = AsyncMock(
        return_value=TranscribeAccepted(job_id="job-0001", status=JobStatus.CREATED)
    )
    transcription_service.wait_and_format = AsyncMock(
        side_effect=PyannoteClientError("upstream-failed")
    )
    extraction_service = AsyncMock()
    extraction_service.extract = AsyncMock()
    service = _service(
        tmp_path,
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )
    accepted = await service.start(b"fake-audio-bytes")
    await service.run_pipeline(accepted.id)

    extraction_service.extract.assert_not_awaited()
    assert not (tmp_path / CONSULTATION_ID / "transcript.txt").exists()
    meta = _meta(tmp_path)
    assert meta["status"] == ConsultationStatus.FAILED
    assert meta["error"] == INTERNAL_SERVER_ERROR_MESSAGE


async def test_extract_failure_keeps_transcript(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _patch_uuid(mocker)
    transcription_service = AsyncMock()
    transcription_service.start_transcription = AsyncMock(
        return_value=TranscribeAccepted(job_id="job-0001", status=JobStatus.CREATED)
    )
    transcription_service.wait_and_format = AsyncMock(return_value=FAKE_TRANSCRIPT)
    extraction_service = AsyncMock()
    extraction_service.extract = AsyncMock(
        side_effect=AnthropicClientError("anthropic-upstream-failed")
    )
    service = _service(
        tmp_path,
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )
    accepted = await service.start(b"fake-audio-bytes")
    await service.run_pipeline(accepted.id)

    consultation_dir = tmp_path / CONSULTATION_ID
    saved_transcript = (consultation_dir / "transcript.txt").read_text(encoding="utf-8")
    assert saved_transcript == FAKE_TRANSCRIPT
    assert not (consultation_dir / "documents.json").exists()
    meta = _meta(tmp_path)
    assert meta["status"] == ConsultationStatus.FAILED
    assert meta["error"] == INTERNAL_SERVER_ERROR_MESSAGE


async def test_retry_extract_regenerates_documents(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _patch_uuid(mocker)
    transcription_service = AsyncMock()
    transcription_service.start_transcription = AsyncMock(
        return_value=TranscribeAccepted(job_id="job-0001", status=JobStatus.CREATED)
    )
    transcription_service.wait_and_format = AsyncMock(return_value=FAKE_TRANSCRIPT)
    extraction_service = AsyncMock()
    extraction_service.extract = AsyncMock(
        side_effect=AnthropicClientError("anthropic-upstream-failed")
    )
    service = _service(
        tmp_path,
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )
    accepted = await service.start(b"fake-audio-bytes")
    await service.run_pipeline(accepted.id)
    extraction_service.extract = AsyncMock(return_value=fake_consultation_documents())
    service = _service(
        tmp_path,
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )
    retry = await service.start_extract(accepted.id)
    assert retry.status == ConsultationStatus.EXTRACTING
    await service.run_extract(accepted.id)
    meta = _meta(tmp_path)
    assert meta["status"] == ConsultationStatus.SUCCEEDED
    assert meta["error"] is None
    assert (tmp_path / CONSULTATION_ID / "documents.json").exists()


async def test_retry_extract_requires_transcript(tmp_path: Path) -> None:
    consultation_dir = tmp_path / CONSULTATION_ID
    consultation_dir.mkdir(parents=True)
    stamp = datetime(2026, 9, 7, 16, 0, 0).isoformat() + "+00:00"
    (consultation_dir / "meta.json").write_text(
        json.dumps(
            {
                "id": CONSULTATION_ID,
                "status": "failed",
                "pyannote_job_id": "job-0001",
                "error": "Internal Server Error",
                "created_at": stamp,
                "updated_at": stamp,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ExtractNotReadyError) as exc_info:
        await _service(tmp_path).start_extract(CONSULTATION_ID)
    assert exc_info.value.message == EXTRACT_NOT_READY_MESSAGE


async def test_retry_extract_rejects_transcribing(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _patch_uuid(mocker)
    transcription_service = AsyncMock()
    transcription_service.start_transcription = AsyncMock(
        return_value=TranscribeAccepted(job_id="job-0001", status=JobStatus.CREATED)
    )
    service = _service(tmp_path, transcription_service=transcription_service)
    accepted = await service.start(b"fake-audio-bytes")
    (tmp_path / CONSULTATION_ID / "transcript.txt").write_text(
        FAKE_TRANSCRIPT, encoding="utf-8"
    )
    with pytest.raises(ExtractNotReadyError):
        await service.start_extract(accepted.id)


async def test_get_unknown_consultation_raises(tmp_path: Path) -> None:
    with pytest.raises(ConsultationNotFoundError) as exc_info:
        _service(tmp_path).get(CONSULTATION_ID)
    assert exc_info.value.message == CONSULTATION_NOT_FOUND_MESSAGE


async def test_get_does_not_return_transcript(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _patch_uuid(mocker)
    transcription_service = AsyncMock()
    transcription_service.start_transcription = AsyncMock(
        return_value=TranscribeAccepted(job_id="job-0001", status=JobStatus.CREATED)
    )
    transcription_service.wait_and_format = AsyncMock(return_value=FAKE_TRANSCRIPT)
    extraction_service = AsyncMock()
    extraction_service.extract = AsyncMock(return_value=fake_consultation_documents())
    service = _service(
        tmp_path,
        transcription_service=transcription_service,
        extraction_service=extraction_service,
    )
    accepted = await service.start(b"fake-audio-bytes")
    await service.run_pipeline(accepted.id)
    result = service.get(accepted.id)
    assert result.documents is not None
    assert result.error is None
    dumped = result.model_dump()
    assert "transcript" not in dumped
    assert dumped["documents"]["medical_record"]["subjective"] == (
        "lorem-ipsum-subjetivo"
    )
