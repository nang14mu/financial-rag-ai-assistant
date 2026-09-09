"""Evaluation script for Query Router precision and routing accuracy."""
import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.router.router import QueryRouter

logger = logging.getLogger(__name__)


def evaluate_router(eval_file: str = "./data/eval/router_questions.jsonl") -> dict:
    """Benchmark routing classification accuracy."""
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"Evaluation file {eval_file} not found.")

    router = QueryRouter()
    total = 0
    correct = 0
    per_class = {}

    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            total += 1
            query = item["query"]
            expected = item["expected_route"]

            decision = router.route(query)
            predicted = decision.route.value

            if expected not in per_class:
                per_class[expected] = {"total": 0, "correct": 0}
            per_class[expected]["total"] += 1

            if predicted == expected:
                correct += 1
                per_class[expected]["correct"] += 1
            else:
                logger.warning(
                    "Mismatch for query: '%s' | Expected: %s, Predicted: %s",
                    query,
                    expected,
                    predicted,
                )

    metrics = {
        "total_queries": total,
        "overall_accuracy": round(correct / total, 4) if total else 0,
        "per_class_accuracy": {
            cls: round(d["correct"] / d["total"], 4) if d["total"] else 0
            for cls, d in per_class.items()
        },
    }
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = evaluate_router()
    print("Router Evaluation Results:", json.dumps(res, indent=2))
