from fastapi import APIRouter

from app.api.v1.process import router as process_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(process_router)
