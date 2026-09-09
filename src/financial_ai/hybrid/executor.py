"""Hybrid execution engine executing SQL and RAG branches concurrently and fusing evidence."""
import logging
from typing import Dict, Any, Optional
from financial_ai.router.schemas import RouteType, RouteDecision
from financial_ai.hybrid.decomposer import QueryDecomposer
from financial_ai.hybrid.fusion import EvidenceFusion, EvidenceContext
from financial_ai.text2sql.generator import Text2SQLGenerator
from financial_ai.text2sql.executor import SQLExecutor
from financial_ai.rag.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)


class HybridExecutor:
    """Coordinates execution across SQL and RAG pipelines."""

    def __init__(
        self,
        sql_generator: Optional[Text2SQLGenerator] = None,
        sql_executor: Optional[SQLExecutor] = None,
        retriever: Optional[DenseRetriever] = None,
        decomposer: Optional[QueryDecomposer] = None,
        fusion: Optional[EvidenceFusion] = None,
    ):
        self.sql_gen = sql_generator or Text2SQLGenerator()
        self.sql_exec = sql_executor or SQLExecutor()
        self.retriever = retriever or DenseRetriever()
        self.decomposer = decomposer or QueryDecomposer()
        self.fusion = fusion or EvidenceFusion()

    def execute(self, decision: RouteDecision) -> EvidenceContext:
        """Execute according to routing decision and return fused EvidenceContext."""
        route = decision.route
        query = decision.analysis.query
        analysis = decision.analysis

        ticker = analysis.tickers[0] if analysis.tickers else None
        fy = analysis.fiscal_years[0] if analysis.fiscal_years else None
        section = analysis.target_sections[0] if analysis.target_sections else None

        sql_result = None
        rag_result = None

        if route == RouteType.SQL_ONLY:
            logger.info("Executing SQL_ONLY branch for '%s'", query)
            sql_query = self.sql_gen.generate(query)
            sql_result = self.sql_exec.execute(sql_query)

        elif route == RouteType.RAG_ONLY:
            logger.info("Executing RAG_ONLY branch for '%s'", query)
            rag_result = self.retriever.retrieve(
                query=query,
                ticker=ticker,
                fiscal_year=fy,
                section=section,
                top_k=4,
            )

        else:  # HYBRID
            logger.info("Executing HYBRID branch for '%s'", query)
            sub_queries = self.decomposer.decompose(query, analysis)

            # 1. SQL sub-branch
            sql_q = sub_queries["sql_subquery"]
            generated_sql = self.sql_gen.generate(sql_q)
            sql_result = self.sql_exec.execute(generated_sql)

            # 2. RAG sub-branch
            rag_q = sub_queries["rag_subquery"]
            rag_result = self.retriever.retrieve(
                query=rag_q,
                ticker=ticker,
                fiscal_year=fy,
                section=section or "Item 7",
                top_k=3,
            )

        # Fuse evidence
        fused = self.fusion.fuse(
            query=query,
            route=route.value,
            sql_result=sql_result,
            rag_result=rag_result,
        )
        return fused
