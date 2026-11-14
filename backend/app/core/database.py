from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Normalize postgresql:// to postgresql+psycopg:// for psycopg3 compatibility
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to provide database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Creates database tables automatically on startup if they do not exist."""
    import app.models  # Ensure all models are imported so Base.metadata knows about them
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
