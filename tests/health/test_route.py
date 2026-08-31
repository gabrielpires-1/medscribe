from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.health.schemas import HealthRead
from app.health.service import HealthService


def test_get_health_returns_ok(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(
        HealthService,
        "check",
        return_value=HealthRead(status="ok"),
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_health_uses_service_status(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        HealthService,
        "check",
        return_value=HealthRead(status="degraded"),
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
