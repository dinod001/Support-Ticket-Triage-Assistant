from fastapi import APIRouter
from app.api.tickets import router as tickets_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(tickets_router)

__all__ = ["api_router"]
