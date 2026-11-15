import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.llm_log import LLMLog

logger = logging.getLogger(__name__)


def record_llm_call(
    db: Session,
    call_type: str,
    model_name: str,
    latency_ms: int,
    success: bool,
    ticket_id: Optional[int] = None,
    error_message: Optional[str] = None
) -> LLMLog:
    """
    Persists audit records of LLM interactions into PostgreSQL llm_logs table.
    Tracks latency, model name, and error status for observability.
    """
    try:
        log_entry = LLMLog(
            ticket_id=ticket_id,
            call_type=call_type,
            model_name=model_name,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record LLM log entry: {str(e)}")
        # Do not raise to prevent breaking main business flow
        return None
