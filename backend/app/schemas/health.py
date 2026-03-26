from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]


class MetricsResponse(BaseModel):
    process_requests_total: int
    process_requests_success: int
    process_requests_partial: int
    process_requests_error: int
