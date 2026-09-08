from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.constants import (
    CONSULTATION_NOT_FOUND_MESSAGE,
    EMPTY_AUDIO_MESSAGE,
    EXTRACT_NOT_READY_MESSAGE,
    ConsultationStatus,
)
from app.consultation.schemas import ConsultationAccepted, ConsultationRead
from app.consultation.service import ConsultationService
from app.exceptions import (
    AnthropicClientError,
    ConsultationNotFoundError,
    ExtractNotReadyError,
    PyannoteClientError,
    PyannoteJobTimeoutError,
)
from tests.fakes import fake_consultation_documents

CONSULTATION_ID = "00000000-0000-4000-8000-000000000001"


def test_create_consultation_returns_202_schema(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "start",
        new_callable=AsyncMock,
        return_value=ConsultationAccepted(
            id=CONSULTATION_ID,
            status=ConsultationStatus.TRANSCRIBING,
        ),
    )
    run_pipeline = mocker.patch.object(
        ConsultationService,
        "run_pipeline",
        new_callable=AsyncMock,
    )
    response = client.post(
        "/consultations",
        files={"file": ("consult-0001.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 202
    assert response.json() == {"id": CONSULTATION_ID, "status": "transcribing"}
    run_pipeline.assert_awaited_once_with(CONSULTATION_ID)


def test_get_consultation_returns_schema(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "get",
        return_value=ConsultationRead(
            id=CONSULTATION_ID,
            status=ConsultationStatus.SUCCEEDED,
            documents=fake_consultation_documents(),
            error=None,
        ),
    )
    response = client.get(f"/consultations/{CONSULTATION_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == CONSULTATION_ID
    assert payload["status"] == "succeeded"
    assert payload["error"] is None
    assert payload["documents"]["medical_record"]["subjective"] == (
        "lorem-ipsum-subjetivo"
    )
    assert "transcript" not in payload


def test_get_consultation_returns_null_documents_while_transcribing(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "get",
        return_value=ConsultationRead(
            id=CONSULTATION_ID,
            status=ConsultationStatus.TRANSCRIBING,
            documents=None,
            error=None,
        ),
    )
    response = client.get(f"/consultations/{CONSULTATION_ID}")
    assert response.status_code == 200
    assert response.json() == {
        "id": CONSULTATION_ID,
        "status": "transcribing",
        "documents": None,
        "error": None,
    }


def test_get_consultation_maps_missing_id_to_404(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "get",
        side_effect=ConsultationNotFoundError(CONSULTATION_NOT_FOUND_MESSAGE),
    )
    response = client.get(f"/consultations/{CONSULTATION_ID}")
    assert response.status_code == 404
    assert response.json()["detail"] == CONSULTATION_NOT_FOUND_MESSAGE


def test_extract_retry_returns_202(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "start_extract",
        new_callable=AsyncMock,
        return_value=ConsultationAccepted(
            id=CONSULTATION_ID,
            status=ConsultationStatus.EXTRACTING,
        ),
    )
    run_extract = mocker.patch.object(
        ConsultationService,
        "run_extract",
        new_callable=AsyncMock,
    )
    response = client.post(f"/consultations/{CONSULTATION_ID}/extract")
    assert response.status_code == 202
    assert response.json() == {"id": CONSULTATION_ID, "status": "extracting"}
    run_extract.assert_awaited_once_with(CONSULTATION_ID)


def test_extract_retry_maps_not_ready_to_409(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "start_extract",
        new_callable=AsyncMock,
        side_effect=ExtractNotReadyError(EXTRACT_NOT_READY_MESSAGE),
    )
    response = client.post(f"/consultations/{CONSULTATION_ID}/extract")
    assert response.status_code == 409
    assert response.json()["detail"] == EXTRACT_NOT_READY_MESSAGE


def test_create_consultation_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/consultations",
        files={"file": ("consult-0001.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == EMPTY_AUDIO_MESSAGE


def test_create_consultation_maps_client_error_to_502(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "start",
        new_callable=AsyncMock,
        side_effect=PyannoteClientError("upstream-failed"),
    )
    mocker.patch.object(
        ConsultationService,
        "run_pipeline",
        new_callable=AsyncMock,
    )
    response = client.post(
        "/consultations",
        files={"file": ("consult-0001.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream-failed"


def test_create_consultation_maps_timeout_to_504(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "start",
        new_callable=AsyncMock,
        side_effect=PyannoteJobTimeoutError("job-0001 timed out"),
    )
    response = client.post(
        "/consultations",
        files={"file": ("consult-0001.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 504
    assert response.json()["detail"] == "job-0001 timed out"


def test_create_consultation_maps_anthropic_error_to_502(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ConsultationService,
        "start",
        new_callable=AsyncMock,
        side_effect=AnthropicClientError("anthropic-upstream-failed"),
    )
    response = client.post(
        "/consultations",
        files={"file": ("consult-0001.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "anthropic-upstream-failed"
