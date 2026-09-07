import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


def pytest_configure() -> None:
    os.environ.setdefault("MEDSCRIBE_PYANNOTE_API_KEY", "fake-api-key")


@pytest.fixture
def client() -> Generator[TestClient]:
    # Settings() runs on import and requires MEDSCRIBE_PYANNOTE_API_KEY.
    from app.main import create_app  # pylint: disable=import-outside-toplevel

    with TestClient(create_app()) as test_client:
        yield test_client
