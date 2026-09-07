from __future__ import annotations

import asyncio
import time

import httpx2

from app.clients.pyannote_schemas import (
    DiarizationJob,
    DiarizeRequest,
    JobCreated,
    MediaInputRequest,
    MediaUploadResponse,
)
from app.config import Settings, get_settings
from app.constants import (
    MEDIA_URL_PREFIX,
    OCTET_STREAM_CONTENT_TYPE,
    PYANNOTE_DIARIZE_PATH,
    PYANNOTE_JOBS_PATH,
    PYANNOTE_JSON_TIMEOUT_SECONDS,
    PYANNOTE_MEDIA_INPUT_PATH,
    PYANNOTE_MEDIA_PUT_TIMEOUT_SECONDS,
    JobStatus,
)
from app.exceptions import (
    PyannoteClientError,
    PyannoteJobFailedError,
    PyannoteJobTimeoutError,
)


class PyannoteClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._settings.pyannote_api_key}"}

    def _api_url(self, path: str) -> str:
        return f"{self._settings.pyannote_base_url.rstrip('/')}{path}"

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, object] | None = None,
    ) -> dict[str, object]:
        url = self._api_url(path)
        try:
            timeout = PYANNOTE_JSON_TIMEOUT_SECONDS
            async with httpx2.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method,
                    url,
                    json=json_body,
                    headers=self._auth_headers(),
                )
        except httpx2.HTTPError as exc:
            raise PyannoteClientError(f"pyannote request failed: {exc}") from exc
        if not response.is_success:
            raise PyannoteClientError(
                f"pyannote returned {response.status_code}: {response.text}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise PyannoteClientError("pyannote returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise PyannoteClientError("pyannote returned a non-object JSON body")
        return payload

    async def create_media_input(self, object_key: str) -> MediaUploadResponse:
        request = MediaInputRequest(url=f"{MEDIA_URL_PREFIX}{object_key}")
        payload = await self._request_json(
            "POST",
            PYANNOTE_MEDIA_INPUT_PATH,
            json_body=request.model_dump(by_alias=True, mode="json"),
        )
        return MediaUploadResponse.model_validate(payload)

    async def put_media(self, presigned_url: str, content: bytes) -> None:
        headers = {"Content-Type": OCTET_STREAM_CONTENT_TYPE}
        try:
            async with httpx2.AsyncClient(
                timeout=PYANNOTE_MEDIA_PUT_TIMEOUT_SECONDS
            ) as client:
                response = await client.put(
                    presigned_url,
                    content=content,
                    headers=headers,
                )
        except httpx2.HTTPError as exc:
            raise PyannoteClientError(f"pyannote media upload failed: {exc}") from exc
        if not response.is_success:
            raise PyannoteClientError(
                "pyannote media upload returned "
                f"{response.status_code}: {response.text}"
            )

    async def upload_audio(self, object_key: str, content: bytes) -> str:
        media_url = f"{MEDIA_URL_PREFIX}{object_key}"
        upload = await self.create_media_input(object_key)
        await self.put_media(upload.url, content)
        return media_url

    async def create_diarize_job(self, media_url: str) -> JobCreated:
        request = DiarizeRequest(url=media_url, transcription=True)
        payload = await self._request_json(
            "POST",
            PYANNOTE_DIARIZE_PATH,
            json_body=request.model_dump(by_alias=True, mode="json"),
        )
        return JobCreated.model_validate(payload)

    async def get_job(self, job_id: str) -> DiarizationJob:
        payload = await self._request_json("GET", f"{PYANNOTE_JOBS_PATH}/{job_id}")
        return DiarizationJob.model_validate(payload)

    async def wait_for_job(self, job_id: str) -> DiarizationJob:
        deadline = time.monotonic() + self._settings.pyannote_poll_timeout_seconds
        while True:
            job = await self.get_job(job_id)
            if job.status == JobStatus.SUCCEEDED:
                return job
            if job.status in {JobStatus.FAILED, JobStatus.CANCELED}:
                raise PyannoteJobFailedError(
                    f"job {job_id} {job.status}",
                    job=job,
                )
            if time.monotonic() >= deadline:
                raise PyannoteJobTimeoutError(f"job {job_id} timed out")
            await asyncio.sleep(self._settings.pyannote_poll_interval_seconds)
