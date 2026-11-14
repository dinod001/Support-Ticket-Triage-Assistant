from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application & Environment
    PROJECT_NAME: str = "Support Ticket Triage Assistant"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000

    # Database Configuration (PostgreSQL default, SQLite fallback for fast testing)
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/triage_db"

    # LLM Provider Configuration ('ollama', 'groq', or 'gemini')
    LLM_PROVIDER: str = "ollama"

    # Ollama Configuration (Local Default)
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:1.5b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # Optional Cloud Providers
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Knowledge Base Path
    KB_DIRECTORY: str = "app/knowledge_base"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
