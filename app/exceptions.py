from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.clients.pyannote_schemas import DiarizationJob


class AppError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmptyAudioError(AppError):
    pass


class PyannoteClientError(AppError):
    pass


class PyannoteJobTimeoutError(PyannoteClientError):
    pass


class PyannoteJobFailedError(PyannoteClientError):
    def __init__(self, message: str, job: DiarizationJob | None = None) -> None:
        super().__init__(message)
        self.job = job


class EmptyTranscriptError(PyannoteClientError):
    pass


class AnthropicClientError(AppError):
    pass


class ConsultationNotFoundError(AppError):
    pass


class ExtractNotReadyError(AppError):
    pass
