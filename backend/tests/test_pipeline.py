import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.data_pipeline import KnowledgeBaseDataPipeline


def test_markdown_chunking_pipeline():
    """Verifies that markdown files are parsed and split into section chunks."""
    kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "knowledge_base"))
    pipeline = KnowledgeBaseDataPipeline(kb_directory=kb_dir)

    chunks = pipeline.load_and_chunk_documents()
    assert len(chunks) > 15  # 9 articles with multiple sections should yield 20+ chunks

    # Check chunk structure
    first_chunk = chunks[0]
    assert first_chunk.chunk_id is not None
    assert first_chunk.article_title is not None
    assert first_chunk.section_heading is not None
    assert len(first_chunk.text) > 20


def test_pipeline_caching(tmp_path):
    """Verifies that pre-computed chunk index can be saved and loaded from disk cache."""
    kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "knowledge_base"))
    cache_file = str(tmp_path / "test_kb_cache.json")

    pipeline = KnowledgeBaseDataPipeline(kb_directory=kb_dir, cache_file=cache_file)
    pipeline.load_and_chunk_documents()

    # Assign dummy embeddings
    for c in pipeline.chunks:
        c.embedding = [0.1, 0.2, 0.3, 0.4]

    pipeline.save_index()
    assert os.path.exists(cache_file)

    # Load in a new pipeline instance
    new_pipeline = KnowledgeBaseDataPipeline(kb_directory=kb_dir, cache_file=cache_file)
    loaded = new_pipeline.load_index()
    assert loaded is True
    assert len(new_pipeline.chunks) == len(pipeline.chunks)
    assert new_pipeline.chunks[0].embedding == [0.1, 0.2, 0.3, 0.4]
