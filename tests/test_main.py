from fastapi.testclient import TestClient

from app.main import create_app

FRONTEND_ORIGIN = "http://localhost:3000"


def test_create_app_exposes_health_route() -> None:
    application = create_app()
    with TestClient(application) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_app_allows_frontend_origin() -> None:
    application = create_app()
    with TestClient(application) as client:
        response = client.get("/health", headers={"Origin": FRONTEND_ORIGIN})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_create_app_allows_frontend_preflight() -> None:
    application = create_app()
    with TestClient(application) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code in {200, 204}
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
