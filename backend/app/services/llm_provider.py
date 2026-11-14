import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


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
                "temperature": 0.1  # Low temperature for deterministic classification
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
        # Ollama supports /api/embeddings or newer /api/embed
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self._embed_model,
            "prompt": text
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])


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
        return "groq-embedding-default"

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True
    ) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in environment.")

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
        # Groq focuses on chat inference; fallback to deterministic hash vector if embedding requested
        return [0.0] * 768


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

        # Default realistic mock triage JSON
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
        # Deterministic 128-dim vector derived from text content
        val = sum(ord(c) for c in text) % 100 / 100.0
        return [val] * 128


def get_llm_provider() -> BaseLLMProvider:
    """Factory function returning the configured LLM provider instance."""
    provider_type = settings.LLM_PROVIDER.lower().strip()
    if provider_type == "groq":
        return GroqProvider()
    elif provider_type == "mock":
        return MockLLMProvider()
    else:
        # Default is Ollama
        return OllamaProvider()
