"""LLM-based semantic financial intent classifier and entity extractor (Tier 2 Router)."""
import json
import re
import logging
from typing import Optional, Any, Dict
from financial_ai.llm import get_llm, extract_llm_text
from financial_ai.router.schemas import RouteType, QueryAnalysis, RouteDecision

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert financial query routing and entity extraction AI.
Analyze the user's financial query, accounting for potential typos, slang, abbreviations, or missing diacritics in Vietnamese/English.

Allowed Companies / Tickers:
- AAPL (Apple, nhà Táo, táo khuyết, appl)
- NVDA (NVIDIA, yến vi, đội xanh)
- MSFT (Microsoft, tiểu phàm, micro, vi nhuyễn)

10-K SEC Report Sections:
- Item 1 (Business, mô tả kinh doanh, chiến lược)
- Item 1A (Risk Factors, rủi ro, thách thức, chuỗi cung ứng)
- Item 7 (MD&A, Management's Discussion and Analysis, giải trình kết quả)

Routing Decision Categories:
1. SQL_ONLY: Pure quantitative query asking for numbers, revenue, profit, EPS, margins, growth percentages, historical metrics.
2. RAG_ONLY: Pure qualitative query asking for business strategy, risk factors, legal issues, management narrative, descriptions.
3. HYBRID: Compound query asking for BOTH quantitative numbers and qualitative explanations/reasons/MD&A context.

Respond ONLY with a valid JSON object matching this exact schema:
{
  "route": "SQL_ONLY" | "RAG_ONLY" | "HYBRID",
  "tickers": ["AAPL"],
  "fiscal_years": [2024],
  "target_sections": ["Item 1A"],
  "primary_metrics": ["total_revenue"],
  "is_quantitative": true,
  "is_qualitative": false,
  "rationale": "Brief explanation of routing decision"
}
"""


class LLMQueryClassifier:
    """Classifies financial query intent and extracts entities using LLM (Tier 2)."""

    def __init__(self, llm: Optional[Any] = None):
        self._llm = llm

    def _get_llm(self) -> Optional[Any]:
        if self._llm is not None:
            return self._llm
        try:
            self._llm = get_llm(temperature=0.0)
            return self._llm
        except Exception as exc:
            logger.warning("Could not initialize LLM for Tier-2 routing: %s", exc)
            return None

    def classify(self, query: str, baseline_analysis: Optional[QueryAnalysis] = None) -> Optional[RouteDecision]:
        """Classify query using LLM and return RouteDecision. Returns None if LLM call fails."""
        llm = self._get_llm()
        if not llm:
            logger.warning("Tier-2 LLM not available. Bypassing LLM classification.")
            return None

        prompt = f"{SYSTEM_PROMPT}\n\nUser Query: \"{query}\"\n\nJSON:"

        try:
            resp = llm.invoke(prompt)
            raw_text = extract_llm_text(resp)

            # Strip markdown formatting
            clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE).strip()
            # Extract JSON block if surrounded by extra text
            match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(0)

            data: Dict[str, Any] = json.loads(clean_text)

            # Normalize RouteType
            route_str = str(data.get("route", "HYBRID")).upper().strip()
            if route_str not in RouteType._value2member_map_:
                route_str = "HYBRID"
            route_type = RouteType(route_str)

            # Merge or fall back on extracted entities
            tickers = data.get("tickers") or (baseline_analysis.tickers if baseline_analysis else [])
            fiscal_years = data.get("fiscal_years") or (baseline_analysis.fiscal_years if baseline_analysis else [])
            target_sections = data.get("target_sections") or (baseline_analysis.target_sections if baseline_analysis else [])
            primary_metrics = data.get("primary_metrics") or (baseline_analysis.primary_metrics if baseline_analysis else [])

            is_quant = bool(data.get("is_quantitative", route_type in (RouteType.SQL_ONLY, RouteType.HYBRID)))
            is_qual = bool(data.get("is_qualitative", route_type in (RouteType.RAG_ONLY, RouteType.HYBRID)))

            analysis = QueryAnalysis(
                query=query,
                tickers=tickers,
                fiscal_years=fiscal_years,
                target_sections=target_sections,
                primary_metrics=primary_metrics,
                is_quantitative=is_quant,
                is_qualitative=is_qual,
                confidence=0.98,
            )

            rationale = data.get("rationale") or f"Tier-2 LLM classified as {route_type.value}"

            logger.info("Tier-2 LLM classified query '%s' -> [%s]", query[:50], route_type.value)
            return RouteDecision(
                route=route_type,
                analysis=analysis,
                rationale=f"[Tier-2 LLM] {rationale}",
            )
        except Exception as exc:
            logger.warning("Tier-2 LLM classification failed for query '%s': %s", query[:50], exc)
            return None
