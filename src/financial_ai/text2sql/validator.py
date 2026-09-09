"""SQL AST validator using sqlglot to strictly enforce read-only and whitelist security guardrails."""
import re
import logging
from typing import Tuple, Optional, Set
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

ALLOWED_TABLES: Set[str] = {
    "v_annual_financial_summary",
    "v_growth_and_margins",
    "v_segment_revenue",
    "companies",
    "financial_facts",
    "dimension_data",
}

FORBIDDEN_KEYWORDS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
]


class SQLValidator:
    """Validates SQL statements for strict read-only execution on approved semantic views."""

    def __init__(self, allowed_tables: Optional[Set[str]] = None):
        self.allowed_tables = allowed_tables or ALLOWED_TABLES

    def validate(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """Check if query is safe, valid SELECT statement on allowed views."""
        if not sql_query or not sql_query.strip():
            return False, "Empty SQL query."

        clean_query = sql_query.strip().rstrip(";").strip()

        # Check for multiple queries (semicolons)
        if ";" in clean_query:
            return False, "Multiple SQL statements detected; only single statement permitted."

        # Regex check for destructive keywords
        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, clean_query, re.IGNORECASE):
                return False, f"Forbidden keyword detected matching pattern '{pattern}'."

        # Parse AST with sqlglot
        try:
            parsed = sqlglot.parse_one(clean_query, read="postgres")
        except Exception as exc:
            # Fallback parse generic
            try:
                parsed = sqlglot.parse_one(clean_query)
            except Exception as inner_exc:
                return False, f"SQL syntax parsing error: {inner_exc}"

        # Must be a Select expression
        if not isinstance(parsed, exp.Select):
            return False, f"Query must be a SELECT statement, got '{type(parsed).__name__}'."

        # Extract CTE aliases so they are not treated as external tables
        cte_aliases = {cte.alias_or_name.lower() for cte in parsed.find_all(exp.CTE) if cte.alias_or_name}

        # Extract and verify external tables
        tables = [t.name.lower() for t in parsed.find_all(exp.Table) if t.name and t.name.lower() not in cte_aliases]
        for table in tables:
            if table not in self.allowed_tables:
                return False, f"Table/View '{table}' is not in allowed whitelist: {sorted(list(self.allowed_tables))}."

        return True, None
