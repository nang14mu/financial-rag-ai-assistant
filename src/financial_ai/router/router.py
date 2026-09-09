"""Query Router deciding between SQL_ONLY, RAG_ONLY, and HYBRID execution paths."""
import logging
from typing import Optional
from financial_ai.router.schemas import RouteType, QueryAnalysis, RouteDecision
from financial_ai.router.analyzer import QueryAnalyzer

logger = logging.getLogger(__name__)


class QueryRouter:
    """Routes user queries to the appropriate engine branch."""

    def __init__(self, analyzer: Optional[QueryAnalyzer] = None):
        self.analyzer = analyzer or QueryAnalyzer()

    def route(self, query: str) -> RouteDecision:
        """Analyze query and return routing decision."""
        analysis = self.analyzer.analyze(query)

        # 1. Compound / Hybrid Decision
        if analysis.is_quantitative and analysis.is_qualitative:
            decision = RouteDecision(
                route=RouteType.HYBRID,
                analysis=analysis,
                rationale="Query requires both structured numerical facts and qualitative 10-K narrative context.",
            )
        # 2. Pure Quantitative -> SQL_ONLY
        elif analysis.is_quantitative and not analysis.is_qualitative:
            decision = RouteDecision(
                route=RouteType.SQL_ONLY,
                analysis=analysis,
                rationale="Query asks for structured financial metrics, figures, or historical comparisons.",
            )
        # 3. Pure Qualitative -> RAG_ONLY
        elif analysis.is_qualitative and not analysis.is_quantitative:
            decision = RouteDecision(
                route=RouteType.RAG_ONLY,
                analysis=analysis,
                rationale="Query asks for qualitative business strategy, risk factors, or management disclosures.",
            )
        # 4. Ambiguous fallback
        else:
            decision = RouteDecision(
                route=RouteType.HYBRID,
                analysis=analysis,
                rationale="Ambiguous query intent; defaulting to Hybrid search for comprehensive coverage.",
            )

        logger.info("Routed query '%s' -> [%s]", query[:60], decision.route.value)
        return decision
