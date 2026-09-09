"""Master script to run end-to-end evaluation suite across all system components."""
import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.evaluation.router_eval import evaluate_router
from financial_ai.evaluation.sql_eval import evaluate_sql
from financial_ai.evaluation.rag_eval import evaluate_rag
from financial_ai.evaluation.hybrid_eval import evaluate_hybrid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_all_evaluations():
    logger.info("==================================================")
    logger.info("FINANCIAL AI ASSISTANT: MASTER EVALUATION SUITE")
    logger.info("==================================================")

    results = {}

    # 1. Router Evaluation
    logger.info("\n[1/4] Running Router Classification Evaluation...")
    router_res = evaluate_router("./data/eval/router_questions.jsonl")
    results["router"] = router_res
    logger.info("Router Accuracy: %s%%", router_res.get("overall_accuracy", 0) * 100)

    # 2. Text-to-SQL Evaluation
    logger.info("\n[2/4] Running Text-to-SQL Execution Evaluation...")
    sql_res = evaluate_sql("./data/eval/sql_questions.jsonl")
    results["sql"] = sql_res
    logger.info("SQL Execution Success Rate: %s%%", sql_res.get("execution_success_rate", 0) * 100)

    # 3. RAG Retrieval Evaluation
    logger.info("\n[3/4] Running RAG Retrieval Evaluation...")
    rag_res = evaluate_rag("./data/eval/rag_questions.jsonl")
    results["rag"] = rag_res
    logger.info("RAG Section Precision: %s%%", rag_res.get("section_precision", 0) * 100)

    # 4. Hybrid Pipeline Evaluation
    logger.info("\n[4/4] Running Hybrid Pipeline Evaluation...")
    hybrid_res = evaluate_hybrid("./data/eval/hybrid_questions.jsonl")
    results["hybrid"] = hybrid_res
    logger.info("Hybrid Full Evidence Rate: %s%%", hybrid_res.get("full_evidence_rate", 0) * 100)

    logger.info("\n==================================================")
    logger.info("FINAL EVALUATION SUMMARY:")
    logger.info(json.dumps(results, indent=2))
    logger.info("==================================================")

    # Save summary report
    out_path = "./data/eval/evaluation_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved evaluation summary to %s", out_path)


if __name__ == "__main__":
    run_all_evaluations()
