import glob
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.prompts.rag_prompt import (
    RAG_DRAFT_SYSTEM_PROMPT,
    RAG_DRAFT_USER_PROMPT,
    NO_ARTICLE_FALLBACK_REPLY
)
from app.services.llm_provider import BaseLLMProvider, get_llm_provider
from app.services.llm_logger import record_llm_call

logger = logging.getLogger(__name__)


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two numeric dense vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0
    return dot_product / (norm_a * norm_b)


class RAGService:
    """
    RAG Retrieval & Reply Drafting Engine.
    Indexes sample Help Articles, performs dense vector retrieval,
    and synthesizes empathetic draft replies with cited sources.
    """

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        kb_directory: Optional[str] = None,
        similarity_threshold: float = 0.35
    ):
        self.provider = provider or get_llm_provider()
        self.kb_directory = kb_directory or self._resolve_kb_dir()
        self.similarity_threshold = similarity_threshold
        self.indexed_articles: List[Dict[str, Any]] = []

    def _resolve_kb_dir(self) -> str:
        """Finds knowledge_base directory whether running from root or backend/."""
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "knowledge_base"),
            os.path.join(os.getcwd(), "backend", "app", "knowledge_base"),
            os.path.join(os.getcwd(), "app", "knowledge_base"),
            settings.KB_DIRECTORY
        ]
        for path in candidates:
            if os.path.exists(path) and os.path.isdir(path):
                return os.path.abspath(path)
        return os.path.abspath(candidates[0])

    async def index_knowledge_base(self) -> int:
        """Loads all markdown articles and generates vector embeddings on startup."""
        search_pattern = os.path.join(self.kb_directory, "*.md")
        files = glob.glob(search_pattern)
        logger.info(f"Indexing {len(files)} knowledge base articles from {self.kb_directory}...")

        articles = []
        for file_path in files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                # Extract title from first H1 heading or filename
                lines = content.splitlines()
                title = filename.replace(".md", "").replace("_", " ").title()
                for line in lines:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                embedding = await self.provider.generate_embedding(f"{title}\n\n{content}")
                articles.append({
                    "filename": filename,
                    "title": title,
                    "content": content,
                    "embedding": embedding
                })
            except Exception as e:
                logger.error(f"Error reading KB article {filename}: {str(e)}")

        self.indexed_articles = articles
        logger.info(f"Successfully indexed {len(self.indexed_articles)} articles.")
        return len(self.indexed_articles)

    async def retrieve_relevant_articles(
        self,
        query: str,
        top_k: int = 2
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Computes query embedding and retrieves top matching articles above threshold."""
        if not self.indexed_articles:
            await self.index_knowledge_base()

        query_embedding = await self.provider.generate_embedding(query)
        scored_articles = []

        for article in self.indexed_articles:
            score = compute_cosine_similarity(query_embedding, article["embedding"])
            scored_articles.append((article, score))

        # Sort by similarity score descending
        scored_articles.sort(key=lambda x: x[1], reverse=True)

        # Filter by threshold
        relevant = [(art, score) for art, score in scored_articles[:top_k] if score >= self.similarity_threshold]
        return relevant

    async def generate_draft_reply(
        self,
        title: str,
        description: str,
        db: Optional[Session] = None,
        ticket_id: Optional[int] = None
    ) -> Tuple[str, List[str]]:
        """
        Retrieves articles and calls LLM to draft a reply citing the sources.
        Returns: Tuple of (draft_reply_text: str, cited_article_titles: List[str])
        """
        start_time = time.time()
        combined_query = f"{title}\n{description}"
        relevant_matches = await self.retrieve_relevant_articles(combined_query, top_k=2)

        # Fallback if no article matches the query with confidence
        if not relevant_matches:
            latency_ms = int((time.time() - start_time) * 1000)
            if db:
                record_llm_call(
                    db=db,
                    call_type="rag_draft_no_match",
                    model_name=self.provider.model_name,
                    latency_ms=latency_ms,
                    success=True,
                    ticket_id=ticket_id
                )
            return NO_ARTICLE_FALLBACK_REPLY, []

        # Construct context from matched articles
        context_parts = []
        cited_titles = []
        for article, score in relevant_matches:
            cited_titles.append(article["title"])
            context_parts.append(f"--- ARTICLE: {article['title']} (Match Confidence: {score:.2f}) ---\n{article['content']}")

        full_context = "\n\n".join(context_parts)
        user_prompt = RAG_DRAFT_USER_PROMPT.format(
            title=title,
            description=description,
            context=full_context
        )

        try:
            draft_text = await self.provider.generate_chat_completion(
                system_prompt=RAG_DRAFT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                json_mode=False
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if db:
                record_llm_call(
                    db=db,
                    call_type="rag_draft",
                    model_name=self.provider.model_name,
                    latency_ms=latency_ms,
                    success=True,
                    ticket_id=ticket_id
                )

            # Ensure citations are explicitly visible if model omitted them
            if not any(f"[{title}]" in draft_text for title in cited_titles):
                draft_text += f"\n\nSources Referenced: {', '.join([f'[{t}]' for t in cited_titles])}"

            return draft_text.strip(), cited_titles

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            err_msg = f"RAG drafting error: {str(e)}"
            logger.error(err_msg)

            if db:
                record_llm_call(
                    db=db,
                    call_type="rag_draft_failed",
                    model_name=self.provider.model_name,
                    latency_ms=latency_ms,
                    success=False,
                    ticket_id=ticket_id,
                    error_message=err_msg
                )

            # Resilient fallback
            return NO_ARTICLE_FALLBACK_REPLY, []
