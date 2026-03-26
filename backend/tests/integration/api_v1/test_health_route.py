from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_healthy() -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_response_structure() -> None:
    response = client.get("/v1/health")
    body = response.json()

    assert "status" in body
    assert body["status"] in ("healthy", "degraded")
