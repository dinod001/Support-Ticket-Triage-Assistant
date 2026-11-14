import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.rag_service import RAGService, compute_cosine_similarity
from app.services.llm_provider import BaseLLMProvider
from app.prompts.rag_prompt import NO_ARTICLE_FALLBACK_REPLY


class MockRAGProvider(BaseLLMProvider):
    """
    Mock LLM Provider for Retrieval Tests.
    Generates deterministic keyword-based embeddings so tests run in milliseconds without network.
    """

    @property
    def model_name(self) -> str:
        return "mock-rag-model"

    @property
    def embed_model_name(self) -> str:
        return "mock-embed"

    async def generate_chat_completion(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        return (
            "Dear customer, based on our Return and Refund Policy, items can be returned within 30 days "
            "of delivery. A refund will be processed to your original payment method. "
            "Reference: [Return and Refund Policy]"
        )

    async def generate_embedding(self, text: str):
        # 4-dimensional semantic toy vector: [refund_score, shipping_score, account_score, damaged_score]
        t = text.lower()
        return [
            1.0 if any(w in t for w in ["refund", "return", "money", "30 days"]) else 0.0,
            1.0 if any(w in t for w in ["shipping", "delivery", "courier", "track", "express"]) else 0.0,
            1.0 if any(w in t for w in ["password", "account", "login", "delete", "2fa"]) else 0.0,
            1.0 if any(w in t for w in ["damaged", "broken", "cracked", "defective"]) else 0.0,
        ]


def test_cosine_similarity_math():
    """Verifies that mathematical cosine similarity calculation is exact."""
    v1 = [1.0, 0.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0, 0.0]
    v_zero = [0.0, 0.0, 0.0, 0.0]

    assert round(compute_cosine_similarity(v1, v2), 4) == 1.0
    assert round(compute_cosine_similarity(v1, v3), 4) == 0.0
    assert compute_cosine_similarity(v1, v_zero) == 0.0


def test_retrieval_returns_correct_article():
    """
    Verifies assessment requirement:
    'one retrieval test that checks the right article is returned for a sample ticket.'
    """
    async def _run():
        provider = MockRAGProvider()
        service = RAGService(provider=provider, similarity_threshold=0.35)
        indexed_count = await service.index_knowledge_base(force_reindex=True)
        assert indexed_count >= 8

        # Sample inquiry about returning an item
        matches = await service.retrieve_relevant_articles(
            query="Can I return an item and get a full refund within 30 days?",
            top_k=1
        )

        assert len(matches) > 0
        top_article, score = matches[0]
        assert "Refund" in top_article["title"]
        assert score > 0.5

    asyncio.run(_run())


def test_retrieval_no_match_honest_fallback():
    """
    Verifies assessment requirement:
    'If nothing relevant is found, the draft should say so instead of inventing a policy.'
    """
    async def _run():
        provider = MockRAGProvider()
        service = RAGService(provider=provider, similarity_threshold=0.50)
        await service.index_knowledge_base(force_reindex=True)

        # Query completely unrelated to e-commerce policies (all dimensions 0.0)
        draft_reply, cited = await service.generate_draft_reply(
            title="How to build a quantum computer?",
            description="Explain qubit entanglement and cryogenic cooling."
        )

        assert cited == []
        assert draft_reply == NO_ARTICLE_FALLBACK_REPLY

    asyncio.run(_run())


if __name__ == "__main__":
    test_cosine_similarity_math()
    test_retrieval_returns_correct_article()
    test_retrieval_no_match_honest_fallback()
    print("ALL RAG RETRIEVAL TESTS PASSED!")
