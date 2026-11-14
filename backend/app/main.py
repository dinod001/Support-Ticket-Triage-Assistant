import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import api_router
from app.services.llm_provider import get_llm_provider
from app.services.triage_service import TriageService
from app.services.rag_service import RAGService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ticket_triage_assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Context Manager.
    Pre-warms heavy resources on server startup:
    1. Initializes database schema tables automatically.
    2. Instantiates singleton LLM Provider, Triage Service, and RAG Service on app.state.
    3. Pre-computes vector embeddings for all Knowledge Base help articles.
    """
    logger.info("Initializing Support Ticket Triage Assistant backend...")

    # 1. Database table initialization
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning(f"Database init warning (will retry on container start): {str(e)}")

    # 2. Warm up singleton services on app.state
    provider = get_llm_provider()
    app.state.provider = provider
    app.state.triage_service = TriageService(provider=provider)
    app.state.rag_service = RAGService(provider=provider)

    # 3. Pre-index Knowledge Base articles
    try:
        count = await app.state.rag_service.index_knowledge_base()
        logger.info(f"Knowledge Base pre-warmed: {count} articles indexed in memory.")
    except Exception as e:
        logger.error(f"Error pre-indexing knowledge base: {str(e)}")

    logger.info("Backend warm-up complete. Ready to receive requests.")
    yield
    logger.info("Shutting down backend services...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-stack AI Support Ticket Triage & RAG Reply Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware (permitting React frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits all localhost ports (Vite 3000 / 5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Support Ticket Triage Assistant API is online.",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }
