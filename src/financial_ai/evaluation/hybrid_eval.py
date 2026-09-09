"""Evaluation script for Hybrid pipeline end-to-end retrieval and execution."""
import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.router.router import QueryRouter
from financial_ai.hybrid.executor import HybridExecutor

logger = logging.getLogger(__name__)


def evaluate_hybrid(eval_file: str = "./data/eval/hybrid_questions.jsonl") -> dict:
    """Benchmark Hybrid pipeline execution and evidence completeness."""
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"Evaluation file {eval_file} not found.")

    router = QueryRouter()
    executor = HybridExecutor()

    total = 0
    sql_success_count = 0
    rag_chunks_found_count = 0

    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            total += 1
            query = item["query"]

            decision = router.route(query)
            evidence = executor.execute(decision)

            if evidence.sql_rows and len(evidence.sql_rows) > 0:
                sql_success_count += 1
            if evidence.retrieved_chunks and len(evidence.retrieved_chunks) > 0:
                rag_chunks_found_count += 1

    metrics = {
        "total_queries": total,
        "sql_evidence_rate": round(sql_success_count / total, 4) if total else 0,
        "rag_evidence_rate": round(rag_chunks_found_count / total, 4) if total else 0,
        "full_evidence_rate": round(min(sql_success_count, rag_chunks_found_count) / total, 4) if total else 0,
    }
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = evaluate_hybrid()
    print("Hybrid Evaluation Results:", json.dumps(res, indent=2))
