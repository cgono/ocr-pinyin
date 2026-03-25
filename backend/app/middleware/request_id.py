from collections.abc import Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = Response(status_code=500)
        try:
            response = await call_next(request)
        except Exception:
            pass  # response stays as the pre-created 500; X-Request-ID set below
        response.headers["X-Request-ID"] = request_id
        return response
