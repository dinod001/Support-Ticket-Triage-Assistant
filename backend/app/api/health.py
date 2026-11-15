from fastapi import APIRouter, Request

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check(request: Request):
    """Healthcheck endpoint for Docker healthchecks and monitoring."""
    indexed_articles = 0
    if hasattr(request.app.state, "rag_service") and request.app.state.rag_service:
        indexed_articles = len(request.app.state.rag_service.indexed_articles)

    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "kb_articles_indexed": indexed_articles
    }
