import hashlib
import json
import logging
import math
import re
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_keyword_embedding(text: str, dim: int = 256) -> List[float]:
    """
    Generates a deterministic semantic term-frequency hash embedding.
    Ensures high cosine similarity for documents sharing keywords and concepts,
    providing zero-latency local retrieval when external embedding APIs are unavailable.
    """
    vector = [0.0] * dim
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    if not words:
        return vector

    # Weight key support vocabulary
    priority_terms = {
        "refund": 3.0, "return": 3.0, "money": 2.5, "days": 2.0,
        "shipping": 3.0, "delivery": 3.0, "courier": 2.5, "tracking": 3.0,
        "damaged": 3.5, "broken": 3.5, "defective": 3.0, "photo": 2.5,
        "password": 3.5, "reset": 3.0, "login": 2.5, "2fa": 3.0,
        "account": 3.0, "delete": 3.5, "privacy": 2.5, "gdpr": 3.0,
        "cancel": 3.5, "cancellation": 3.5, "dispatched": 2.5,
        "payment": 3.0, "card": 2.5, "declined": 3.0, "billing": 3.0,
        "subscription": 3.5, "upgrade": 2.5, "downgrade": 2.5,
        "customs": 3.5, "international": 3.0, "duties": 3.0
    }

    for word in words:
        weight = priority_terms.get(word, 1.0)
        idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % dim
        vector[idx] += weight

    # Normalize to unit length for cosine similarity
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0.0:
        vector = [v / norm for v in vector]

    return vector


class BaseLLMProvider(ABC):
    """Abstract Base Class defining the contract for swappable LLM providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the chat model used by this provider."""
        pass

    @property
    @abstractmethod
    def embed_model_name(self) -> str:
        """Name of the embedding model used by this provider."""
        pass

    @abstractmethod
    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True
    ) -> str:
        """Generates a text or structured JSON chat completion from the model."""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generates a dense vector embedding for the input text."""
        pass


class OllamaProvider(BaseLLMProvider):
    """Local default LLM provider communicating with Dockerized Ollama container."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._chat_model = chat_model or settings.OLLAMA_CHAT_MODEL
        self._embed_model = embed_model or settings.OLLAMA_EMBED_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    @property
    def model_name(self) -> str:
        return self._chat_model

    @property
    def embed_model_name(self) -> str:
        return self._embed_model

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self._chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def generate_embedding(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self._embed_model,
            "prompt": text
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.warning(f"Ollama embeddings fallback: {str(e)}")
            return generate_keyword_embedding(text)


class GroqProvider(BaseLLMProvider):
    """Optional free-tier hosted cloud provider using Groq's high-speed inference."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self._model = model or settings.GROQ_MODEL
        self.base_url = "https://api.groq.com/openai/v1"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def embed_model_name(self) -> str:
        return "groq-semantic-embed"

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True
    ) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in environment or .env file.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_embedding(self, text: str) -> List[float]:
        # Try local Ollama if running, otherwise use semantic keyword embedding
        try:
            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(url, json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text})
                if res.status_code == 200:
                    return res.json().get("embedding", [])
        except Exception:
            pass
        return generate_keyword_embedding(text, dim=256)


class MockLLMProvider(BaseLLMProvider):
    """Mock provider for instantaneous offline testing and CI workflows."""

    def __init__(self, model: str = "mock-model"):
        self._model = model
        self.custom_chat_response: Optional[str] = None

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def embed_model_name(self) -> str:
        return "mock-embed"

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True
    ) -> str:
        if self.custom_chat_response:
            return self.custom_chat_response

        return json.dumps({
            "category": "Refund",
            "priority": "high",
            "sentiment": "negative",
            "summary": "Customer requests a full refund for a damaged monitor.",
            "entities": {
                "order_number": "ORD-12345",
                "tracking_id": "TRK-9900",
                "product_name": "UltraWide Monitor"
            }
        })

    async def generate_embedding(self, text: str) -> List[float]:
        return generate_keyword_embedding(text, dim=128)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function returning the configured LLM provider instance."""
    provider_type = settings.LLM_PROVIDER.lower().strip()
    if provider_type == "groq":
        return GroqProvider()
    elif provider_type == "mock":
        return MockLLMProvider()
    else:
        return OllamaProvider()
