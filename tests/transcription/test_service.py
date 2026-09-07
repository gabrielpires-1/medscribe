import logging
from datetime import UTC, datetime
from pathlib import Path
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
from app.constants import INTERNAL_SERVER_ERROR_MESSAGE, JobStatus
from app.exceptions import EmptyAudioError, PyannoteClientError, PyannoteJobFailedError
from app.transcription.schemas import TranscribeAccepted
from app.transcription.service import (
    TranscriptionService,
    format_turn_level_transcript,
    format_user_error,
)


def _settings(tmp_path: Path | None = None) -> Settings:
    return Settings(
        pyannote_api_key="fake-api-key",
        transcription_output_dir=tmp_path or Path("data/transcriptions"),
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


def test_format_user_error_includes_message_and_timestamp() -> None:
    occurred_at = datetime(2026, 9, 7, 14, 33, 4, 358000, tzinfo=UTC)
    result = format_user_error(occurred_at)
    assert result == (f"{INTERNAL_SERVER_ERROR_MESSAGE}\n{occurred_at.isoformat()}")


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


async def test_persist_job_result_writes_txt_transcript(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
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
    await TranscriptionService(settings=_settings(tmp_path)).persist_job_result(
        "job-0001"
    )
    saved_text = (tmp_path / "job-0001.txt").read_text(encoding="utf-8")
    assert saved_text == "[SPEAKER_00] fake-turn-one\n[SPEAKER_01] fake-turn-two"


async def test_persist_job_result_writes_user_error_txt(
    mocker: MockerFixture,
    tmp_path: Path,
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
    await TranscriptionService(settings=_settings(tmp_path)).persist_job_result(
        "job-0001"
    )
    saved_text = (tmp_path / "job-0001.txt").read_text(encoding="utf-8")
    assert saved_text == format_user_error(occurred_at)
    assert "job-0001" not in saved_text
    assert "failed" not in saved_text.lower()
    assert "fake-upstream-error" not in saved_text


async def test_persist_job_result_logs_internal_error(
    mocker: MockerFixture,
    tmp_path: Path,
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
        await TranscriptionService(settings=_settings(tmp_path)).persist_job_result(
            "job-0001"
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "ERROR"
    assert record.msg == (
        "transcription persist failed job_id=%s status=%s detail=%s occurred_at=%s"
    )
    assert record.args == (
        "job-0001",
        JobStatus.FAILED,
        "fake-upstream-error",
        occurred_at.isoformat(),
    )
