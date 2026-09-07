from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.constants import JobStatus
from app.exceptions import PyannoteClientError
from app.transcription.schemas import TranscribeAccepted
from app.transcription.service import TranscriptionService


def test_transcribe_returns_202_schema(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        TranscriptionService,
        "start_transcription",
        new_callable=AsyncMock,
        return_value=TranscribeAccepted(
            job_id="job-0001",
            status=JobStatus.CREATED,
        ),
    )
    persist = mocker.patch.object(
        TranscriptionService,
        "persist_job_result",
        new_callable=AsyncMock,
    )
    response = client.post(
        "/transcribe",
        files={"file": ("consult-0001.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 202
    assert response.json() == {"job_id": "job-0001", "status": "created"}
    persist.assert_awaited_once_with("job-0001")


def test_transcribe_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/transcribe",
        files={"file": ("consult-0001.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400


def test_transcribe_maps_client_error_to_502(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        TranscriptionService,
        "start_transcription",
        new_callable=AsyncMock,
        side_effect=PyannoteClientError("upstream-failed"),
    )
    mocker.patch.object(
        TranscriptionService,
        "persist_job_result",
        new_callable=AsyncMock,
    )
    response = client.post(
        "/transcribe",
        files={"file": ("consult-0001.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream-failed"
