from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from app.clients.pyannote_client import PyannoteClient
from app.clients.pyannote_schemas import DiarizationJob, JobCreated, MediaUploadResponse
from app.config import Settings
from app.constants import JobStatus
from app.exceptions import (
    PyannoteClientError,
    PyannoteJobFailedError,
    PyannoteJobTimeoutError,
)


def _settings(pyannote_poll_timeout_seconds: float = 600) -> Settings:
    return Settings(
        pyannote_api_key="fake-api-key",
        anthropic_api_key="fake-anthropic-key",
        pyannote_poll_interval_seconds=0,
        pyannote_poll_timeout_seconds=pyannote_poll_timeout_seconds,
    )


def _json_response(payload: dict[str, object], status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.is_success = 200 <= status_code < 300
    response.status_code = status_code
    response.text = ""
    response.json.return_value = payload
    return response


def _patch_async_client(mocker: MockerFixture, response: MagicMock) -> AsyncMock:
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client.put = AsyncMock(return_value=response)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    mocker.patch(
        "app.clients.pyannote_client.httpx2.AsyncClient",
        return_value=client,
    )
    return client


async def test_create_media_input_returns_presigned_url(mocker: MockerFixture) -> None:
    response = _json_response({"url": "https://upload.example.test/presigned"}, 201)
    http_client = _patch_async_client(mocker, response)
    client = PyannoteClient(settings=_settings())
    upload = await client.create_media_input("object-0001")
    assert isinstance(upload, MediaUploadResponse)
    assert upload.url == "https://upload.example.test/presigned"
    method, url = http_client.request.call_args.args
    assert method == "POST"
    assert url.endswith("/v1/media/input")
    assert http_client.request.call_args.kwargs["json"] == {
        "url": "media://object-0001",
    }


async def test_upload_audio_puts_bytes_and_returns_media_url(
    mocker: MockerFixture,
) -> None:
    client = PyannoteClient(settings=_settings())
    mocker.patch.object(
        client,
        "create_media_input",
        new_callable=AsyncMock,
        return_value=MediaUploadResponse(url="https://upload.example.test/presigned"),
    )
    put_media = mocker.patch.object(client, "put_media", new_callable=AsyncMock)
    media_url = await client.upload_audio("object-0001", b"fake-audio-bytes")
    assert media_url == "media://object-0001"
    put_media.assert_awaited_once_with(
        "https://upload.example.test/presigned",
        b"fake-audio-bytes",
    )


async def test_put_media_sends_octet_stream_without_bearer(
    mocker: MockerFixture,
) -> None:
    response = _json_response({}, 200)
    http_client = _patch_async_client(mocker, response)
    await PyannoteClient(settings=_settings()).put_media(
        "https://upload.example.test/presigned",
        b"fake-audio-bytes",
    )
    http_client.put.assert_awaited_once()
    (_url,) = http_client.put.call_args.args
    assert _url == "https://upload.example.test/presigned"
    headers = http_client.put.call_args.kwargs["headers"]
    assert headers["Content-Type"] == "application/octet-stream"
    assert "Authorization" not in headers


async def test_create_diarize_job_includes_transcription_true(
    mocker: MockerFixture,
) -> None:
    response = _json_response({"jobId": "job-0001", "status": "created"})
    http_client = _patch_async_client(mocker, response)
    created = await PyannoteClient(settings=_settings()).create_diarize_job(
        "media://object-0001"
    )
    assert isinstance(created, JobCreated)
    assert created.job_id == "job-0001"
    assert created.status == JobStatus.CREATED
    body = http_client.request.call_args.kwargs["json"]
    assert body["transcription"] is True
    assert body["url"] == "media://object-0001"
    assert body["model"] == "precision-2"
    headers = http_client.request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer fake-api-key"


async def test_get_job_parses_diarization_job(mocker: MockerFixture) -> None:
    response = _json_response(
        {
            "jobId": "job-0001",
            "status": "succeeded",
            "createdAt": "2024-02-20T12:00:00Z",
            "output": {
                "diarization": [
                    {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.0},
                ],
                "turnLevelTranscription": [
                    {
                        "start": 0.0,
                        "end": 1.0,
                        "text": "lorem-ipsum-not-real",
                        "speaker": "SPEAKER_00",
                    }
                ],
            },
        }
    )
    _patch_async_client(mocker, response)
    job = await PyannoteClient(settings=_settings()).get_job("job-0001")
    assert isinstance(job, DiarizationJob)
    assert job.job_id == "job-0001"
    assert job.status == JobStatus.SUCCEEDED
    assert job.output is not None
    assert job.output.turn_level_transcription is not None
    assert job.output.turn_level_transcription[0].text == "lorem-ipsum-not-real"


async def test_wait_for_job_returns_succeeded_job(mocker: MockerFixture) -> None:
    client = PyannoteClient(settings=_settings())
    mocker.patch.object(
        client,
        "get_job",
        new_callable=AsyncMock,
        side_effect=[
            DiarizationJob(job_id="job-0001", status=JobStatus.CREATED),
            DiarizationJob(job_id="job-0001", status=JobStatus.SUCCEEDED),
        ],
    )
    sleep = mocker.patch(
        "app.clients.pyannote_client.asyncio.sleep",
        new_callable=AsyncMock,
    )
    job = await client.wait_for_job("job-0001")
    assert job.status == JobStatus.SUCCEEDED
    sleep.assert_awaited_once()


async def test_wait_for_job_raises_on_failed(mocker: MockerFixture) -> None:
    client = PyannoteClient(settings=_settings())
    failed = DiarizationJob(job_id="job-0001", status=JobStatus.FAILED)
    mocker.patch.object(
        client,
        "get_job",
        new_callable=AsyncMock,
        return_value=failed,
    )
    with pytest.raises(PyannoteJobFailedError) as exc_info:
        await client.wait_for_job("job-0001")
    assert exc_info.value.job is failed


async def test_wait_for_job_raises_on_timeout(mocker: MockerFixture) -> None:
    client = PyannoteClient(settings=_settings(pyannote_poll_timeout_seconds=0))
    mocker.patch.object(
        client,
        "get_job",
        new_callable=AsyncMock,
        return_value=DiarizationJob(job_id="job-0001", status=JobStatus.PENDING),
    )
    with pytest.raises(PyannoteJobTimeoutError):
        await client.wait_for_job("job-0001")


async def test_create_media_input_raises_on_http_error(mocker: MockerFixture) -> None:
    response = _json_response({"message": "upstream-failed"}, status_code=502)
    _patch_async_client(mocker, response)
    with pytest.raises(PyannoteClientError):
        await PyannoteClient(settings=_settings()).create_media_input("object-0001")
