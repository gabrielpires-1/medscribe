from app.exceptions import (
    AppError,
    EmptyAudioError,
    PyannoteClientError,
    PyannoteJobFailedError,
    PyannoteJobTimeoutError,
)


def test_app_error_stores_message() -> None:
    error = AppError("fake-failure")
    assert error.message == "fake-failure"
    assert str(error) == "fake-failure"


def test_empty_audio_error_is_app_error() -> None:
    error = EmptyAudioError("audio file is empty")
    assert error.message == "audio file is empty"
    assert isinstance(error, AppError)


def test_pyannote_client_error_is_app_error() -> None:
    error = PyannoteClientError("upstream-failed")
    assert error.message == "upstream-failed"
    assert isinstance(error, AppError)


def test_pyannote_job_timeout_error_is_client_error() -> None:
    error = PyannoteJobTimeoutError("job-0001 timed out")
    assert isinstance(error, PyannoteClientError)
    assert error.message == "job-0001 timed out"


def test_pyannote_job_failed_error_stores_job() -> None:
    error = PyannoteJobFailedError("job-0001 failed", job=None)
    assert error.job is None
    assert error.message == "job-0001 failed"
