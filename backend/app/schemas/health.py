from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]


class DailyCostEntry(BaseModel):
    total_usd: float
    total_sgd: float
    request_count: int


class MetricsResponse(BaseModel):
    process_requests_total: int
    process_requests_success: int
    process_requests_partial: int
    process_requests_error: int
    daily_costs: dict[str, DailyCostEntry] = Field(default_factory=dict)
