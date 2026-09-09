"""RAG retrieval evaluation script benchmarking recall and keyword hit rate."""
import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath("src"))

from typing import Dict, Any, List
from financial_ai.rag.dense_retriever import DenseRetriever
from financial_ai.rag.indexer import ChromaIndexer

logger = logging.getLogger(__name__)


def evaluate_rag(eval_file: str = "./data/eval/rag_questions.jsonl") -> Dict[str, Any]:
    """Evaluate retrieval precision and keyword coverage against benchmark questions."""
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"Evaluation file {eval_file} not found.")

    retriever = DenseRetriever(indexer=ChromaIndexer())
    total_queries = 0
    keyword_hits = 0
    section_match_count = 0

    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            total_queries += 1

            query = item["query"]
            ticker = item.get("ticker")
            expected_sec = item.get("section")
            keywords = [k.lower() for k in item.get("keywords", [])]

            results = retriever.retrieve(
                query=query,
                ticker=ticker,
                section=expected_sec,
                top_k=3,
            )

            # Check if any keyword matches
            combined_text = " ".join([r["text"].lower() for r in results])
            if any(kw in combined_text for kw in keywords):
                keyword_hits += 1

            # Check section match
            if any(r.get("metadata", {}).get("section") == expected_sec for r in results):
                section_match_count += 1

    metrics = {
        "total_queries": total_queries,
        "keyword_hit_rate": round(keyword_hits / total_queries, 4) if total_queries else 0,
        "section_precision": round(section_match_count / total_queries, 4) if total_queries else 0,
    }
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = evaluate_rag()
    print("RAG Evaluation Results:", json.dumps(res, indent=2))
