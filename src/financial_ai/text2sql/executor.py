"""Safe SQL executor with AST validation and error recovery."""
import logging
from typing import Dict, Any, List, Optional
from financial_ai.text2sql.validator import SQLValidator
from financial_ai.text2sql.result_formatter import format_sql_result
from financial_ai.db.repositories import execute_safe_select

logger = logging.getLogger(__name__)


class SQLExecutor:
    """Validates and executes read-only SQL queries against the financial database."""

    def __init__(self, validator: Optional[SQLValidator] = None):
        self.validator = validator or SQLValidator()

    def execute(self, sql_query: str) -> Dict[str, Any]:
        """Validate and execute query, returning structured execution state."""
        clean_query = sql_query.strip().rstrip(";").strip()
        is_valid, err_msg = self.validator.validate(clean_query)

        if not is_valid:
            logger.warning("SQL Validation Failed: %s | Query: %s", err_msg, clean_query)
            return {
                "success": False,
                "error": err_msg,
                "query": clean_query,
                "rows": [],
                "markdown_table": "",
            }

        try:
            rows = execute_safe_select(clean_query)
            md_table = format_sql_result(rows)
            return {
                "success": True,
                "error": None,
                "query": clean_query,
                "rows": rows,
                "row_count": len(rows),
                "markdown_table": md_table,
            }
        except Exception as exc:
            logger.error("SQL Execution Exception: %s | Query: %s", exc, clean_query)
            return {
                "success": False,
                "error": str(exc),
                "query": clean_query,
                "rows": [],
                "markdown_table": "",
            }
