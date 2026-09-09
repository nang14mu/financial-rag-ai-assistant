"""Text-to-SQL Generator using semantic views and LLM orchestration with offline rule fallback."""
import os
import re
import logging
from typing import Dict, Any, Optional
from financial_ai.llm import get_llm, extract_llm_text
from financial_ai.text2sql.schema_provider import SchemaProvider
from financial_ai.text2sql.validator import SQLValidator

logger = logging.getLogger(__name__)


class Text2SQLGenerator:
    """Generates SQL queries over financial semantic views using mandatory LLM."""

    def __init__(
        self,
        schema_provider: Optional[SchemaProvider] = None,
        validator: Optional[SQLValidator] = None,
        llm: Optional[Any] = None,
    ):
        self.schema_provider = schema_provider or SchemaProvider()
        self.validator = validator or SQLValidator()
        self.llm = llm or get_llm(temperature=0.0)

    def generate(self, question: str) -> str:
        """Convert natural language financial question into safe SQL query via LLM.
        
        Raises:
            RuntimeError: If LLM is not available, invocation fails, or generated SQL is invalid.
        """
        if not self.llm:
            raise RuntimeError("Text2SQLGenerator requires an active LLM. No LLM instance available.")

        prompt = (
            f"You are an expert financial SQL analyst querying a PostgreSQL database containing official SEC financial facts.\n"
            f"{self.schema_provider.get_full_prompt_context()}\n\n"
            f"Question: {question}\n\n"
            f"Requirements:\n"
            f"- Output ONLY the executable SQL query.\n"
            f"- Do NOT wrap in markdown backticks or provide any explanations.\n"
            f"- Use only the allowed views: v_annual_financial_summary, v_growth_and_margins, v_segment_revenue, or companies.\n"
        )
        try:
            resp = self.llm.invoke(prompt)
            raw_sql = extract_llm_text(resp)
            clean_sql = re.sub(r"^```sql\s*|\s*```$", "", raw_sql, flags=re.IGNORECASE).strip()
            clean_sql = clean_sql.rstrip(";") + ";"
        except Exception as exc:
            logger.error("Mandatory LLM Text-to-SQL generation failed: %s", exc)
            raise RuntimeError(f"LLM Text-to-SQL generation failed: {exc}") from exc

        is_valid, err = self.validator.validate(clean_sql)
        if not is_valid:
            logger.error("LLM generated invalid SQL: %s | Query: %s", err, clean_sql)
            raise RuntimeError(f"LLM generated invalid SQL query: {err}. (Query: {clean_sql})")

        return clean_sql
