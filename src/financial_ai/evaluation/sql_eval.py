"""Evaluation script for Text-to-SQL generation, validation, and execution accuracy."""
import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.text2sql.generator import Text2SQLGenerator
from financial_ai.text2sql.executor import SQLExecutor

logger = logging.getLogger(__name__)


def evaluate_sql(eval_file: str = "./data/eval/sql_questions.jsonl") -> dict:
    """Benchmark SQL valid syntax rate and execution success rate."""
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"Evaluation file {eval_file} not found.")

    generator = Text2SQLGenerator()
    executor = SQLExecutor()

    total_queries = 0
    valid_syntax_count = 0
    execution_success_count = 0
    rows_returned_count = 0

    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            total_queries += 1
            query = item["query"]

            sql = generator.generate(query)
            is_valid, _ = generator.validator.validate(sql)
            if is_valid:
                valid_syntax_count += 1

            exec_res = executor.execute(sql)
            if exec_res["success"]:
                execution_success_count += 1
                if exec_res["rows"]:
                    rows_returned_count += 1

    metrics = {
        "total_queries": total_queries,
        "valid_syntax_rate": round(valid_syntax_count / total_queries, 4) if total_queries else 0,
        "execution_success_rate": round(execution_success_count / total_queries, 4) if total_queries else 0,
        "data_retrieval_rate": round(rows_returned_count / total_queries, 4) if total_queries else 0,
    }
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = evaluate_sql()
    print("SQL Evaluation Results:", json.dumps(res, indent=2))
