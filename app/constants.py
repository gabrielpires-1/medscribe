from enum import StrEnum
from typing import Final


class HealthStatus(StrEnum):
    OK = "ok"


class JobStatus(StrEnum):
    PENDING = "pending"
    CREATED = "created"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"
    RUNNING = "running"


class DiarizationModel(StrEnum):
    PRECISION_2 = "precision-2"


class TranscriptionModel(StrEnum):
    PARAKEET_TDT_06B_V3 = "parakeet-tdt-0.6b-v3"


TERMINAL_JOB_STATUSES: Final[frozenset[JobStatus]] = frozenset(
    {
        JobStatus.SUCCEEDED,
        JobStatus.CANCELED,
        JobStatus.FAILED,
    }
)

MEDIA_URL_PREFIX: Final[str] = "media://"
PYANNOTE_MEDIA_INPUT_PATH: Final[str] = "/v1/media/input"
PYANNOTE_DIARIZE_PATH: Final[str] = "/v1/diarize"
PYANNOTE_JOBS_PATH: Final[str] = "/v1/jobs"
PYANNOTE_JSON_TIMEOUT_SECONDS: Final[float] = 30.0
PYANNOTE_MEDIA_PUT_TIMEOUT_SECONDS: Final[float] = 120.0
OCTET_STREAM_CONTENT_TYPE: Final[str] = "application/octet-stream"
TRANSCRIPTION_FILE_SUFFIX: Final[str] = ".txt"
INTERNAL_SERVER_ERROR_MESSAGE: Final[str] = "Internal Server Error"
