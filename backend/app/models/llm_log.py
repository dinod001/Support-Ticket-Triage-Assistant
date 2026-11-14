from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.core.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True)

    # 'triage', 'rag_draft', 'embedding'
    call_type = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    latency_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<LLMLog model={self.model_name} type={self.call_type} latency={self.latency_ms}ms success={self.success}>"
