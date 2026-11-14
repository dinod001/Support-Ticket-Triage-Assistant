import glob
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Check if chromadb is available in the environment
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


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


class DocumentChunk(BaseModel):
    chunk_id: str
    source_file: str
    article_title: str
    section_heading: str
    text: str
    embedding: List[float] = Field(default_factory=list)


class KnowledgeBaseDataPipeline:
    """
    Dedicated Data Ingestion & ChromaDB Vector Pipeline.
    Loads raw markdown Help Articles, parses headings, chunks content semantically,
    generates vector embeddings (nomic-embed-text via Ollama), and indexes into ChromaDB.
    """

    def __init__(
        self,
        kb_directory: str,
        chroma_db_dir: Optional[str] = None,
        cache_file: Optional[str] = None
    ):
        self.kb_directory = kb_directory
        self.cache_file = cache_file or os.path.join(kb_directory, ".indexed_kb_cache.json")
        self.chroma_db_dir = chroma_db_dir or os.path.join(os.path.dirname(kb_directory), "chroma_data")
        self.chunks: List[DocumentChunk] = []
        self.chroma_client = None
        self.chroma_collection = None

        if CHROMADB_AVAILABLE:
            try:
                os.makedirs(self.chroma_db_dir, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_dir)
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="support_kb_articles",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"ChromaDB initialized at: {self.chroma_db_dir}")
            except Exception as e:
                logger.warning(f"ChromaDB initialization error: {str(e)}. Using fallback index.")

    def load_and_chunk_documents(self) -> List[DocumentChunk]:
        """Scans all markdown files in KB directory and splits them into semantic section chunks."""
        search_pattern = os.path.join(self.kb_directory, "*.md")
        files = glob.glob(search_pattern)
        logger.info(f"Data Pipeline: Ingesting {len(files)} markdown documents from {self.kb_directory}...")

        all_chunks: List[DocumentChunk] = []

        for file_path in files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read().strip()

                chunks = self._chunk_markdown(raw_text, filename)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Data Pipeline: Failed to process {filename}: {str(e)}")

        self.chunks = all_chunks
        logger.info(f"Data Pipeline: Chunking complete. Generated {len(self.chunks)} semantic chunks.")
        return self.chunks

    def _chunk_markdown(self, text: str, filename: str) -> List[DocumentChunk]:
        """
        Parses Markdown:
        1. Extracts primary # Title
        2. Splits by ## Section headings so each chunk has focused, coherent context.
        """
        lines = text.splitlines()
        article_title = filename.replace(".md", "").replace("_", " ").title()

        # Find H1 Title
        for line in lines:
            if line.startswith("# "):
                article_title = line[2:].strip()
                break

        # Split into sections based on '## '
        sections = re.split(r"\n(?=##\s+)", text)
        chunks: List[DocumentChunk] = []

        chunk_idx = 0
        for section in sections:
            section = section.strip()
            if not section:
                continue

            section_heading = "General Overview"
            content_text = section

            if section.startswith("## "):
                first_newline = section.find("\n")
                if first_newline != -1:
                    section_heading = section[3:first_newline].strip()
                    content_text = section[first_newline:].strip()
                else:
                    section_heading = section[3:].strip()
                    content_text = section_heading

            chunk_text = f"Article: {article_title}\nSection: {section_heading}\n\n{content_text}"

            chunk = DocumentChunk(
                chunk_id=f"{filename}_{chunk_idx}",
                source_file=filename,
                article_title=article_title,
                section_heading=section_heading,
                text=chunk_text,
                embedding=[]
            )
            chunks.append(chunk)
            chunk_idx += 1

        return chunks

    async def run_pipeline(self, provider: Any, force_reindex: bool = False) -> List[DocumentChunk]:
        """
        Executes end-to-end pipeline:
        1. Chunks documents and generates embeddings (e.g. nomic-embed-text).
        2. Indexes into ChromaDB persistent collection if available.
        3. Saves index to cache.
        """
        if not force_reindex and self.load_index():
            test_embed = await provider.generate_embedding("test")
            if self.chunks and len(self.chunks[0].embedding) == len(test_embed):
                logger.info(f"Data Pipeline: Loaded {len(self.chunks)} chunks from persistent cache.")
                return self.chunks

        # Load & chunk
        self.load_and_chunk_documents()

        # Generate embeddings
        logger.info("Data Pipeline: Computing embeddings for chunks...")
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in self.chunks:
            embedding = await provider.generate_embedding(chunk.text)
            chunk.embedding = embedding
            ids.append(chunk.chunk_id)
            embeddings.append(embedding)
            documents.append(chunk.text)
            metadatas.append({
                "source_file": chunk.source_file,
                "article_title": chunk.article_title,
                "section_heading": chunk.section_heading
            })

        # Add to ChromaDB if available
        if self.chroma_collection and embeddings and len(embeddings[0]) > 0:
            try:
                self.chroma_collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                logger.info(f"Data Pipeline: Upserted {len(ids)} chunks into ChromaDB collection.")
            except Exception as e:
                logger.warning(f"Data Pipeline: ChromaDB upsert warning: {str(e)}")

        self.save_index()
        logger.info(f"Data Pipeline: Pipeline execution complete. {len(self.chunks)} chunks indexed.")
        return self.chunks

    def save_index(self) -> None:
        """Persists indexed chunks and vectors to JSON cache."""
        try:
            data = [chunk.model_dump() for chunk in self.chunks]
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            logger.info(f"Data Pipeline: Index saved to {self.cache_file}")
        except Exception as e:
            logger.warning(f"Data Pipeline: Could not write cache file: {str(e)}")

    def load_index(self) -> bool:
        """Loads pre-computed chunks and embeddings from disk if available."""
        if not os.path.exists(self.cache_file):
            return False
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.chunks = [DocumentChunk.model_validate(item) for item in data]
            return len(self.chunks) > 0
        except Exception as e:
            logger.warning(f"Data Pipeline: Failed to read cache: {str(e)}")
            return False

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 2,
        min_similarity: float = 0.35
    ) -> List[Dict[str, Any]]:
        """
        Performs vector search across all indexed chunks using ChromaDB if active,
        or cosine similarity fallback.
        """
        # If ChromaDB collection is active and has documents
        if self.chroma_collection and self.chroma_collection.count() > 0:
            try:
                results = self.chroma_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                if results and results["ids"] and len(results["ids"][0]) > 0:
                    scored = []
                    for i in range(len(results["ids"][0])):
                        dist = results["distances"][0][i] if "distances" in results and results["distances"] else 0.0
                        # Cosine distance: similarity = 1 - distance
                        similarity = 1.0 - dist
                        if similarity >= min_similarity:
                            meta = results["metadatas"][0][i]
                            doc = results["documents"][0][i]
                            dummy_chunk = DocumentChunk(
                                chunk_id=results["ids"][0][i],
                                source_file=meta.get("source_file", ""),
                                article_title=meta.get("article_title", ""),
                                section_heading=meta.get("section_heading", ""),
                                text=doc,
                                embedding=query_embedding
                            )
                            scored.append({
                                "chunk": dummy_chunk,
                                "score": similarity,
                                "title": meta.get("article_title", ""),
                                "section": meta.get("section_heading", ""),
                                "content": doc
                            })
                    return scored
            except Exception as e:
                logger.warning(f"ChromaDB query fallback: {str(e)}")

        # High-speed fallback
        scored = []
        for chunk in self.chunks:
            score = compute_cosine_similarity(query_embedding, chunk.embedding)
            if score >= min_similarity:
                scored.append({
                    "chunk": chunk,
                    "score": score,
                    "title": chunk.article_title,
                    "section": chunk.section_heading,
                    "content": chunk.text
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
