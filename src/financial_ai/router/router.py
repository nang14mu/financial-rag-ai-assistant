"""Query Router deciding between SQL_ONLY, RAG_ONLY, and HYBRID execution paths with cascading LLM fallback."""
import logging
from typing import Optional
from financial_ai.router.schemas import RouteType, QueryAnalysis, RouteDecision
from financial_ai.router.analyzer import QueryAnalyzer
from financial_ai.router.llm_classifier import LLMQueryClassifier

logger = logging.getLogger(__name__)


class QueryRouter:
    """Routes user queries using a 2-Tier Cascading Architecture (Fast Heuristics -> LLM Semantic Fallback)."""

    def __init__(
        self,
        analyzer: Optional[QueryAnalyzer] = None,
        llm_classifier: Optional[LLMQueryClassifier] = None,
        confidence_threshold: float = 0.85,
        enable_llm_fallback: bool = True,
    ):
        self.analyzer = analyzer or QueryAnalyzer()
        self.llm_classifier = llm_classifier
        self.confidence_threshold = confidence_threshold
        self.enable_llm_fallback = enable_llm_fallback

    def route(self, query: str) -> RouteDecision:
        """Analyze query and return routing decision using cascading logic."""
        # Tier 1: Fast Heuristic Analysis (<1ms)
        analysis = self.analyzer.analyze(query)

        # Check whether Tier 2 LLM classification should be triggered
        is_ambiguous = (not analysis.is_quantitative and not analysis.is_qualitative)
        needs_fallback = (
            self.enable_llm_fallback
            and (
                analysis.confidence < self.confidence_threshold
                or not analysis.tickers
                or is_ambiguous
            )
        )

        if needs_fallback:
            if self.llm_classifier is None:
                self.llm_classifier = LLMQueryClassifier()

            llm_decision = self.llm_classifier.classify(query, baseline_analysis=analysis)
            if llm_decision is not None:
                logger.info("Cascaded query '%s' to Tier-2 LLM -> [%s]", query[:60], llm_decision.route.value)
                return llm_decision

        # Tier 1 Decision Logic (when confident or as fallback if LLM is unavailable)
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

        logger.info("Tier-1 Routed query '%s' -> [%s]", query[:60], decision.route.value)
        return decision

