"""Integration tests for the OpenAPI spec endpoint and CORS configuration."""
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_json_returns_200() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_openapi_json_is_valid_schema() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert "openapi" in body
    assert "info" in body
    assert "paths" in body


def test_openapi_includes_process_route() -> None:
    response = client.get("/openapi.json")
    body = response.json()
    paths = body.get("paths", {})
    assert "/v1/process" in paths
    assert "post" in paths["/v1/process"]


def test_openapi_process_route_has_binary_content_types() -> None:
    response = client.get("/openapi.json")
    body = response.json()
    post_op = body["paths"]["/v1/process"]["post"]
    content = post_op["requestBody"]["content"]
    assert "image/jpeg" in content
    assert "image/png" in content
    assert "image/webp" in content


def test_openapi_cors_get_allowed() -> None:
    response = client.get(
        "/openapi.json",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
