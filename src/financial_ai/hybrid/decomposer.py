"""Decomposes compound hybrid queries into targeted SQL and RAG sub-queries."""
import re
import logging
from typing import Dict, Any, Optional
from financial_ai.router.schemas import QueryAnalysis

logger = logging.getLogger(__name__)


class QueryDecomposer:
    """Splits complex queries into independent structured and unstructured questions."""

    def decompose(self, query: str, analysis: Optional[QueryAnalysis] = None) -> Dict[str, str]:
        """Produce separate sub-questions for SQL and RAG."""
        # Clean query
        q_clean = query.strip()

        # Heuristic split on conjunctions e.g. "và", "and", "song song với"
        parts = re.split(r"\s+(?:và|and|đồng thời)\s+", q_clean, flags=re.IGNORECASE)

        if len(parts) >= 2:
            sql_part = parts[0].strip()
            rag_part = " ".join(parts[1:]).strip()

            # Ensure ticker context is preserved in both sub-queries
            ticker_str = f"({', '.join(analysis.tickers)})" if analysis and analysis.tickers else ""
            return {
                "sql_subquery": f"{sql_part} {ticker_str}".strip(),
                "rag_subquery": f"{rag_part} {ticker_str}".strip(),
            }

        # Fallback if no explicit conjunction
        ticker_str = f"{analysis.tickers[0]}" if analysis and analysis.tickers else ""
        return {
            "sql_subquery": f"Financial numbers and metrics for {ticker_str} {query}",
            "rag_subquery": f"Management explanation, context, and strategy for {ticker_str} {query}",
        }
