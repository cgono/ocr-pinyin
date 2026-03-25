"""Tests for RequestIdMiddleware behaviour (#2, #5)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.middleware.request_id import RequestIdMiddleware


def _make_app(*, raise_in_route: bool = False) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ok")
    async def ok_route(request: Request) -> PlainTextResponse:
        return PlainTextResponse(request.state.request_id)

    if raise_in_route:
        @app.get("/boom")
        async def boom_route() -> None:
            raise RuntimeError("intentional error")

    return app


# --- #5: middleware sets X-Request-ID header ---


def test_middleware_sets_x_request_id_header_on_success() -> None:
    client = TestClient(_make_app())
    response = client.get("/ok")
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]  # non-empty


def test_middleware_x_request_id_is_valid_uuid_format() -> None:
    import re
    uuid_re = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    client = TestClient(_make_app())
    response = client.get("/ok")
    assert uuid_re.match(response.headers["x-request-id"])


def test_middleware_request_state_request_id_matches_response_header() -> None:
    """The request_id in state (used by route handler) matches the X-Request-ID header."""
    client = TestClient(_make_app())
    response = client.get("/ok")
    assert response.text == response.headers["x-request-id"]


def test_middleware_generates_unique_id_per_request() -> None:
    client = TestClient(_make_app())
    r1 = client.get("/ok")
    r2 = client.get("/ok")
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


# --- #2: X-Request-ID set even when inner route raises ---


def test_middleware_sets_x_request_id_header_on_server_error() -> None:
    client = TestClient(_make_app(raise_in_route=True), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]
