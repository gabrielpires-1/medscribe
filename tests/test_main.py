from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_exposes_health_route() -> None:
    application = create_app()
    with TestClient(application) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
