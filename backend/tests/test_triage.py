import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.triage_service import TriageService
from app.services.llm_provider import BaseLLMProvider


class MockTriageProvider(BaseLLMProvider):
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "mock-triage-model"

    @property
    def embed_model_name(self) -> str:
        return "mock-embed"

    async def generate_chat_completion(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp

    async def generate_embedding(self, text: str):
        return [0.1] * 128


def test_triage_valid_json():
    """Test 1: Valid structured JSON response parsed cleanly."""
    async def _run():
        valid_json = """{
            "category": "Refund",
            "priority": "high",
            "sentiment": "frustrated",
            "summary": "Customer demands refund for broken display.",
            "entities": {"order_number": "ORD-12345", "product_name": "Display"}
        }"""
        provider = MockTriageProvider([valid_json])
        service = TriageService(provider=provider)

        result, was_fallback = await service.execute_triage(
            title="Screen arrived broken",
            description="The box was crushed and screen is cracked. Need refund."
        )

        assert was_fallback is False
        assert result.category == "Refund"
        assert result.priority == "high"
        assert result.sentiment == "frustrated"
        assert result.entities["order_number"] == "ORD-12345"
        assert provider.call_count == 1

    asyncio.run(_run())


def test_triage_retry_succeeds():
    """Test 2: Invalid JSON on first call, successful on retry."""
    async def _run():
        invalid_first = "Sorry, here is the result: {category: Refund ... (malformed)"
        valid_retry = """{
            "category": "Shipping",
            "priority": "medium",
            "sentiment": "neutral",
            "summary": "Customer inquiring about courier tracking status.",
            "entities": {"tracking_id": "TRK-8899"}
        }"""
        provider = MockTriageProvider([invalid_first, valid_retry])
        service = TriageService(provider=provider)

        result, was_fallback = await service.execute_triage(
            title="Where is my shipment?",
            description="Tracking says pending for 3 days."
        )

        assert was_fallback is False
        assert result.category == "Shipping"
        assert result.entities["tracking_id"] == "TRK-8899"
        assert provider.call_count == 2

    asyncio.run(_run())


def test_triage_fallback_to_manual():
    """Test 3: Both initial and retry fail -> Gracefully falls back to 'needs manual triage'."""
    async def _run():
        invalid_first = "Malformed 1"
        invalid_second = "Malformed 2 still not json"
        provider = MockTriageProvider([invalid_first, invalid_second])
        service = TriageService(provider=provider)

        result, was_fallback = await service.execute_triage(
            title="Weird error message on checkout",
            description="I am getting error code 999128."
        )

        assert was_fallback is True
        assert result.category == "needs manual triage"
        assert result.priority == "medium"
        assert "manual review required" in result.summary.lower()
        assert provider.call_count == 2

    asyncio.run(_run())


if __name__ == "__main__":
    test_triage_valid_json()
    test_triage_retry_succeeds()
    test_triage_fallback_to_manual()
    print("ALL 3 TRIAGE TESTS PASSED DIRECTLY!")
