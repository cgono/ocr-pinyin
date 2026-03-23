"""Shared test helpers for integration and contract test suites.

These are plain module-level utilities (not pytest fixtures) used by
tests in different subdirectories.  They are importable because
pyproject.toml adds the 'tests' directory to pythonpath.
"""
from __future__ import annotations

from starlette.requests import Request

from app.adapters.ocr_provider import RawOcrSegment

PNG_1X1_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2$\x8f"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class StubOcrProvider:
    def __init__(self, segments: list[RawOcrSegment]) -> None:
        self._segments = segments

    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        _ = (image_bytes, content_type)
        return self._segments


def _request_with_body(body: bytes, content_type: str) -> Request:
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/process",
        "raw_path": b"/v1/process",
        "query_string": b"",
        "headers": [(b"content-type", content_type.encode("ascii"))],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
    }
    return Request(scope, receive)
