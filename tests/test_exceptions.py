from app.exceptions import AppError


def test_app_error_stores_message() -> None:
    error = AppError("fake-failure")
    assert error.message == "fake-failure"
    assert str(error) == "fake-failure"
