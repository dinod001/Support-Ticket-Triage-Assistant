import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.pipeline.data_pipeline import KnowledgeBaseDataPipeline, compute_cosine_similarity
from app.prompts.rag_prompt import (
    RAG_DRAFT_SYSTEM_PROMPT,
    RAG_DRAFT_USER_PROMPT,
    NO_ARTICLE_FALLBACK_REPLY
)
from app.services.llm_provider import BaseLLMProvider, get_llm_provider
from app.services.llm_logger import record_llm_call

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG Retrieval & Reply Drafting Engine.
    Powered by the KnowledgeBaseDataPipeline for section-level semantic chunking,
    vector embedding, persistent indexing, and cited response drafting.
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
        self.pipeline = KnowledgeBaseDataPipeline(kb_directory=self.kb_directory)

    @property
    def indexed_articles(self) -> List[Any]:
        """Provides access to indexed chunks for health checks and status."""
        return self.pipeline.chunks

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

    async def index_knowledge_base(self, force_reindex: bool = False) -> int:
        """Executes the data pipeline to chunk documents and generate/load vector embeddings."""
        chunks = await self.pipeline.run_pipeline(provider=self.provider, force_reindex=force_reindex)
        return len(chunks)

    async def retrieve_relevant_articles(
        self,
        query: str,
        top_k: int = 2
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Embeds the incoming user query and searches the indexed chunks via cosine similarity.
        Returns: List of Tuple[Dict of article metadata, similarity score]
        """
        if not self.pipeline.chunks:
            await self.index_knowledge_base()

        query_embedding = await self.provider.generate_embedding(query)
        matches = self.pipeline.query(
            query_embedding=query_embedding,
            top_k=top_k,
            min_similarity=self.similarity_threshold
        )

        results = []
        for match in matches:
            article_dict = {
                "filename": match["chunk"].source_file,
                "title": match["title"],
                "section": match["section"],
                "content": match["content"]
            }
            results.append((article_dict, match["score"]))

        return results

    async def generate_draft_reply(
        self,
        title: str,
        description: str,
        db: Optional[Session] = None,
        ticket_id: Optional[int] = None
    ) -> Tuple[str, List[str]]:
        """
        Retrieves relevant semantic chunks and drafts an empathetic reply with exact source citations.
        Returns: Tuple of (draft_reply_text: str, cited_article_titles: List[str])
        """
        start_time = time.time()
        combined_query = f"{title}\n{description}"
        relevant_matches = await self.retrieve_relevant_articles(combined_query, top_k=2)

        # Fallback if no article meets the confidence threshold
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

        # Construct context from matched chunks
        context_parts = []
        cited_titles = []
        for article, score in relevant_matches:
            if article["title"] not in cited_titles:
                cited_titles.append(article["title"])
            context_parts.append(
                f"--- SOURCE: {article['title']} > {article['section']} (Match: {score:.2f}) ---\n{article['content']}"
            )

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

            # Ensure citations are clearly appended if model omitted them
            if not any(f"[{t}]" in draft_text for t in cited_titles):
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

            return NO_ARTICLE_FALLBACK_REPLY, []
