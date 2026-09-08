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


class ConsultationStatus(StrEnum):
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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
INTERNAL_SERVER_ERROR_MESSAGE: Final[str] = "Internal Server Error"
EMPTY_AUDIO_MESSAGE: Final[str] = "audio file is empty"
CONSULTATION_NOT_FOUND_MESSAGE: Final[str] = "consultation not found"
EXTRACT_NOT_READY_MESSAGE: Final[str] = "transcript is not available"
CONSULTATION_META_FILENAME: Final[str] = "meta.json"
CONSULTATION_TRANSCRIPT_FILENAME: Final[str] = "transcript.txt"
CONSULTATION_DOCUMENTS_FILENAME: Final[str] = "documents.json"
CONSULTATION_JSON_INDENT: Final[int] = 2
ANTHROPIC_REFUSAL_MESSAGE: Final[str] = "anthropic refused to generate output"
ANTHROPIC_MISSING_PARSED_OUTPUT_MESSAGE: Final[str] = (
    "anthropic returned no parsed output"
)
