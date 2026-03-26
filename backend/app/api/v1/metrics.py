from fastapi import APIRouter

from app.core.metrics import metrics_store
from app.schemas.health import MetricsResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    return MetricsResponse(**metrics_store.snapshot())
