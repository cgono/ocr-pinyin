from fastapi import APIRouter

from app.core.metrics import metrics_store
from app.schemas.health import DailyCostEntry, MetricsResponse
from app.services import budget_service

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    daily_costs = {
        date: DailyCostEntry(**entry)
        for date, entry in budget_service.daily_cost_store.snapshot().items()
    }
    return MetricsResponse(**metrics_store.snapshot(), daily_costs=daily_costs)
