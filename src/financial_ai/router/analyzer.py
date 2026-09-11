"""Analyzes financial queries and extracts entity mentions, metrics, and intent signals."""
import re
from typing import List
from financial_ai.router.schemas import QueryAnalysis
from financial_ai.router.rules import (
    QUANT_KEYWORDS,
    QUAL_KEYWORDS,
    TICKER_ALIASES,
    match_hybrid_patterns,
    normalize_query_text,
)


class QueryAnalyzer:
    """Extracts tickers, fiscal years, sections, metrics, and quantitative/qualitative signals."""

    def analyze(self, query: str) -> QueryAnalysis:
        q_lower = query.lower()
        q_norm = normalize_query_text(query)

        # 1. Extract Tickers (Standard symbols + Aliases/Slangs)
        tickers: List[str] = []
        if re.search(r"\b(nvda|nvidia)\b", q_lower):
            tickers.append("NVDA")
        if re.search(r"\b(aapl|apple)\b", q_lower):
            tickers.append("AAPL")
        if re.search(r"\b(msft|microsoft)\b", q_lower):
            tickers.append("MSFT")

        for pattern, symbol in TICKER_ALIASES.items():
            if symbol not in tickers and re.search(pattern, q_lower):
                tickers.append(symbol)

        # 2. Extract Fiscal Years
        years = [int(y) for y in re.findall(r"\b(202[0-9])\b", q_lower)]

        # 3. Extract Target 10-K Sections
        sections: List[str] = []
        if re.search(r"\b(item\s*1a|mục\s*1a|muc\s*1a|risk\s*factors)\b", q_norm):
            sections.append("Item 1A")
        elif re.search(r"\b(item\s*1|mục\s*1|muc\s*1|business)\b", q_norm):
            sections.append("Item 1")
        elif re.search(r"\b(item\s*7|mục\s*7|muc\s*7|md&a|mda|management[\'’]s discussion)\b", q_norm):
            sections.append("Item 7")

        # 4. Extract Metrics
        metrics: List[str] = []
        if any(w in q_norm for w in ["doanh thu", "revenue", "sales"]):
            metrics.append("total_revenue")
        if any(w in q_norm for w in ["net income", "lợi nhuận", "profit"]):
            metrics.append("net_income")
        if any(w in q_norm for w in ["gross margin", "biên lợi nhuận", "biên gộp"]):
            metrics.append("gross_margin_pct")
        if any(w in q_norm for w in ["r&d", "nghiên cứu"]):
            metrics.append("research_and_development")
        if any(w in q_norm for w in ["eps", "earnings per share"]):
            metrics.append("diluted_eps")

        # 5. Determine Quantitative vs Qualitative signals
        has_quant = any(k in q_norm for k in QUANT_KEYWORDS) or len(metrics) > 0
        has_qual = any(k in q_norm for k in QUAL_KEYWORDS) or len(sections) > 0

        # Check for explicit hybrid patterns
        is_hybrid = match_hybrid_patterns(query)
        if is_hybrid:
            has_quant = True
            has_qual = True

        # Determine confidence score
        if is_hybrid:
            confidence = 0.95 if tickers else 0.85
        elif (has_quant != has_qual) and tickers:
            confidence = 0.92
        elif (has_quant != has_qual) and not tickers:
            confidence = 0.70  # Missing or misspelled ticker
        elif not has_quant and not has_qual:
            confidence = 0.40  # Ambiguous intent or misspelled keywords
        else:
            confidence = 0.75  # Mixed signals without explicit hybrid pattern

        return QueryAnalysis(
            query=query,
            tickers=tickers,
            fiscal_years=years,
            target_sections=sections,
            primary_metrics=metrics,
            is_quantitative=has_quant,
            is_qualitative=has_qual,
            confidence=confidence,
        )

