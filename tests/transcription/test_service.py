import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from app.clients.pyannote_client import PyannoteClient
from app.clients.pyannote_schemas import (
    DiarizationJob,
    DiarizationJobOutput,
    JobCreated,
    TranscriptionSegment,
)
from app.config import Settings
from app.constants import JobStatus
from app.exceptions import (
    EmptyAudioError,
    EmptyTranscriptError,
    PyannoteClientError,
    PyannoteJobFailedError,
    PyannoteJobTimeoutError,
)
from app.transcription.schemas import TranscribeAccepted
from app.transcription.service import TranscriptionService, format_turn_level_transcript


def _settings() -> Settings:
    return Settings(
        pyannote_api_key="fake-api-key",
        anthropic_api_key="fake-anthropic-key",
    )


def test_format_turn_level_transcript_joins_speaker_lines() -> None:
    segments = [
        TranscriptionSegment(
            start=0.0, end=1.0, text="fake-turn-one", speaker="SPEAKER_00"
        ),
        TranscriptionSegment(
            start=1.0, end=2.0, text="fake-turn-two", speaker="SPEAKER_01"
        ),
    ]
    result = format_turn_level_transcript(segments)
    assert result == "[SPEAKER_00] fake-turn-one\n[SPEAKER_01] fake-turn-two"


async def test_start_transcription_returns_accepted(mocker: MockerFixture) -> None:
    mocker.patch.object(
        PyannoteClient,
        "upload_audio",
        new_callable=AsyncMock,
        return_value="media://object-0001",
    )
    mocker.patch.object(
        PyannoteClient,
        "create_diarize_job",
        new_callable=AsyncMock,
        return_value=JobCreated(job_id="job-0001", status=JobStatus.CREATED),
    )
    result = await TranscriptionService(settings=_settings()).start_transcription(
        b"fake-audio-bytes"
    )
    assert isinstance(result, TranscribeAccepted)
    assert result.job_id == "job-0001"
    assert result.status == JobStatus.CREATED


async def test_start_transcription_rejects_empty_audio() -> None:
    with pytest.raises(EmptyAudioError):
        await TranscriptionService(settings=_settings()).start_transcription(b"")


async def test_start_transcription_propagates_client_error(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        PyannoteClient,
        "upload_audio",
        new_callable=AsyncMock,
        side_effect=PyannoteClientError("upstream-failed"),
    )
    with pytest.raises(PyannoteClientError):
        await TranscriptionService(settings=_settings()).start_transcription(
            b"fake-audio-bytes"
        )


async def test_wait_and_format_returns_transcript(mocker: MockerFixture) -> None:
    job = DiarizationJob(
        job_id="job-0001",
        status=JobStatus.SUCCEEDED,
        output=DiarizationJobOutput(
            turn_level_transcription=[
                TranscriptionSegment(
                    start=0.0, end=1.0, text="fake-turn-one", speaker="SPEAKER_00"
                ),
                TranscriptionSegment(
                    start=1.0, end=2.0, text="fake-turn-two", speaker="SPEAKER_01"
                ),
            ]
        ),
    )
    mocker.patch.object(
        PyannoteClient,
        "wait_for_job",
        new_callable=AsyncMock,
        return_value=job,
    )
    result = await TranscriptionService(settings=_settings()).wait_and_format(
        "job-0001"
    )
    assert result == "[SPEAKER_00] fake-turn-one\n[SPEAKER_01] fake-turn-two"


async def test_wait_and_format_raises_on_failed_job(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    occurred_at = datetime(2026, 9, 7, 14, 33, 4, 358000, tzinfo=UTC)
    failed = DiarizationJob(
        job_id="job-0001",
        status=JobStatus.FAILED,
        updated_at=occurred_at,
        output=DiarizationJobOutput(error="fake-upstream-error"),
    )
    mocker.patch.object(
        PyannoteClient,
        "wait_for_job",
        new_callable=AsyncMock,
        side_effect=PyannoteJobFailedError("job-0001 failed", job=failed),
    )
    with caplog.at_level(logging.ERROR, logger="app.transcription.service"):
        with pytest.raises(PyannoteJobFailedError):
            await TranscriptionService(settings=_settings()).wait_and_format("job-0001")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "ERROR"
    assert record.msg == (
        "transcription wait failed job_id=%s status=%s detail=%s occurred_at=%s"
    )
    assert record.args == (
        "job-0001",
        JobStatus.FAILED,
        "fake-upstream-error",
        occurred_at.isoformat(),
    )


async def test_wait_and_format_raises_on_empty_turns(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    occurred_at = datetime(2026, 9, 7, 14, 33, 4, 358000, tzinfo=UTC)
    job = DiarizationJob(
        job_id="job-0001",
        status=JobStatus.SUCCEEDED,
        updated_at=occurred_at,
        output=DiarizationJobOutput(),
    )
    mocker.patch.object(
        PyannoteClient,
        "wait_for_job",
        new_callable=AsyncMock,
        return_value=job,
    )
    with caplog.at_level(logging.ERROR, logger="app.transcription.service"):
        with pytest.raises(EmptyTranscriptError):
            await TranscriptionService(settings=_settings()).wait_and_format("job-0001")
    assert len(caplog.records) == 1


async def test_wait_and_format_raises_on_timeout(mocker: MockerFixture) -> None:
    mocker.patch.object(
        PyannoteClient,
        "wait_for_job",
        new_callable=AsyncMock,
        side_effect=PyannoteJobTimeoutError("job-0001 timed out"),
    )
    with pytest.raises(PyannoteJobTimeoutError):
        await TranscriptionService(settings=_settings()).wait_and_format("job-0001")
