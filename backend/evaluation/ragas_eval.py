"""
RAGAS Framework Automated Evaluation Pipeline
=============================================
Computes the four standard RAGAS metrics for Retrieval-Augmented Generation:
1. Faithfulness (Groundedness against retrieved context, zero-hallucination guard)
2. Answer Relevance (Direct alignment to customer query)
3. Context Precision (Signal-to-noise ratio in top retrieved context)
4. Context Recall (Completeness of retrieved policy clauses)

Requirements:
    pip install ragas datasets langchain-community

Usage:
    python -m evaluation.ragas_eval
"""

import asyncio
import os
import sys

# Ensure backend root is on sys.path
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.llm_provider import get_llm_provider
from app.services.rag_service import RAGService

# Benchmark Golden Dataset for Ragas Evaluation
GOLDEN_EVAL_DATASET = [
    {
        "question": "I received unworn shoes in their original box. Can I get a full refund to my credit card?",
        "ground_truth": "Yes. Unworn items in their original packaging and condition are eligible for a full refund within 30 days of delivery. Refunds are credited to the original payment method within 5-7 business days.",
    },
    {
        "question": "My monitor display arrived shattered in the delivery box. What should I do?",
        "ground_truth": "Report damaged items within 48 hours of delivery with photographic evidence of the damage and shipping label. A replacement unit will be dispatched immediately at zero cost.",
    },
    {
        "question": "Where is my parcel? Standard domestic delivery is delayed past 7 days.",
        "ground_truth": "Standard domestic delivery takes 3 to 5 business days. If delayed past 7 business days, our support team will open an inquiry with the courier and initiate a replacement or refund if lost.",
    },
    {
        "question": "How do I permanently delete my account and personal data under GDPR?",
        "ground_truth": "To request permanent account deletion, submit a request via Settings > Privacy or contact privacy@company.com. Account data is permanently deleted within 30 days.",
    },
]


async def run_ragas_evaluation():
    print("=" * 80)
    print("  RAGAS FRAMEWORK ADVANCED RAG EVALUATION")
    print("=" * 80)

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevance,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as e:
        print("\n[!] The 'ragas' and 'datasets' packages are required to run this script.")
        print("    Install them by running: pip install ragas datasets langchain-community")
        print(f"    Missing module error: {e}")
        print("\nTip: To run the zero-dependency benchmark without external packages, run:")
        print("    python -m evaluation.benchmark\n")
        return

    # Initialize RAG Service
    provider = get_llm_provider()
    rag_service = RAGService(provider=provider)
    await rag_service.index_knowledge_base()

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    print("\n>>> Collecting RAG generation outputs for Golden Dataset...")

    for item in GOLDEN_EVAL_DATASET:
        query = item["question"]
        matches = await rag_service.retrieve_relevant_articles(query, top_k=2)
        retrieved_texts = [m[0]["content"] for m in matches] if matches else ["No relevant articles found."]

        draft_reply, _ = await rag_service.generate_draft_reply(
            title="Customer Inquiry",
            description=query
        )

        questions.append(query)
        answers.append(draft_reply)
        contexts.append(retrieved_texts)
        ground_truths.append(item["ground_truth"])

    # Build HuggingFace Dataset
    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    hf_dataset = Dataset.from_dict(dataset_dict)

    print(">>> Running Ragas evaluation metrics (Faithfulness, Answer Relevance, Context Precision, Context Recall)...")

    results = evaluate(
        dataset=hf_dataset,
        metrics=[
            faithfulness,
            answer_relevance,
            context_precision,
            context_recall,
        ],
    )

    print("\n" + "=" * 80)
    print("  RAGAS EVALUATION METRIC SCORES:")
    print("=" * 80)
    print(results)
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_ragas_evaluation())
