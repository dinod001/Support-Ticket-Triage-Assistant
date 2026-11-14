import json
import logging
import time
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.prompts.triage_prompt import (
    TRIAGE_SYSTEM_PROMPT,
    TRIAGE_RETRY_PROMPT,
    build_triage_user_prompt
)
from app.schemas.triage import TriageResult
from app.services.llm_provider import BaseLLMProvider, get_llm_provider
from app.services.llm_logger import record_llm_call

logger = logging.getLogger(__name__)


class TriageService:
    """
    Executes automated ticket classification, priority assessment, sentiment analysis,
    and entity extraction with strict schema validation, retry logic, and resilient fallback.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def execute_triage(
        self,
        title: str,
        description: str,
        db: Optional[Session] = None,
        ticket_id: Optional[int] = None
    ) -> Tuple[TriageResult, bool]:
        """
        Runs triage pipeline.
        Returns: Tuple of (TriageResult, was_fallback_used: bool)
        """
        start_time = time.time()
        user_prompt = build_triage_user_prompt(title, description)
        raw_response = ""
        error_details = ""

        # Attempt 1: Initial call
        try:
            raw_response = await self.provider.generate_chat_completion(
                system_prompt=TRIAGE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                json_mode=True
            )
            result = self._parse_and_validate(raw_response)
            latency_ms = int((time.time() - start_time) * 1000)

            if db:
                record_llm_call(
                    db=db,
                    call_type="triage",
                    model_name=self.provider.model_name,
                    latency_ms=latency_ms,
                    success=True,
                    ticket_id=ticket_id
                )
            return result, False

        except Exception as e:
            error_details = str(e)
            logger.warning(f"Initial triage attempt failed: {error_details}. Triggering 1-time retry.")

        # Attempt 2: Corrective Retry
        try:
            retry_prompt = TRIAGE_RETRY_PROMPT.format(
                error_details=error_details,
                previous_response=raw_response[:500]
            )
            retry_response = await self.provider.generate_chat_completion(
                system_prompt=TRIAGE_SYSTEM_PROMPT,
                user_prompt=retry_prompt,
                json_mode=True
            )
            result = self._parse_and_validate(retry_response)
            latency_ms = int((time.time() - start_time) * 1000)

            if db:
                record_llm_call(
                    db=db,
                    call_type="triage_retry",
                    model_name=self.provider.model_name,
                    latency_ms=latency_ms,
                    success=True,
                    ticket_id=ticket_id
                )
            return result, False

        except Exception as retry_err:
            latency_ms = int((time.time() - start_time) * 1000)
            final_err_msg = f"Retry failed: {str(retry_err)}"
            logger.error(f"Triage retry failed. Gracefully falling back to manual triage: {final_err_msg}")

            if db:
                record_llm_call(
                    db=db,
                    call_type="triage_failed",
                    model_name=self.provider.model_name,
                    latency_ms=latency_ms,
                    success=False,
                    ticket_id=ticket_id,
                    error_message=final_err_msg
                )

            # Resilient Fallback: Never crash the application
            fallback_result = TriageResult(
                category="needs manual triage",
                priority="medium",
                sentiment="neutral",
                summary=f"{title.strip()[:100]} - (Auto-triage failed, manual review required)",
                entities={}
            )
            return fallback_result, True

    def _parse_and_validate(self, raw_text: str) -> TriageResult:
        """Cleans raw LLM output and validates against TriageResult schema."""
        cleaned = raw_text.strip()

        # Strip accidental markdown code blocks if model included them
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        # Parse JSON
        parsed_data = json.loads(cleaned)

        # Validate with Pydantic
        return TriageResult.model_validate(parsed_data)
