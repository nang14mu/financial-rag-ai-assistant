"""FastAPI endpoint routes handling financial assistant operations."""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from financial_ai.api.schemas import (
    QueryRequest,
    QueryResponse,
    SQLDirectRequest,
    SQLDirectResponse,
    RAGDirectRequest,
    RAGDirectResponse,
    HealthResponse,
)
from financial_ai.router.router import QueryRouter
from financial_ai.router.schemas import RouteDecision, RouteType
from financial_ai.hybrid.executor import HybridExecutor
from financial_ai.generation.answer_generator import FinancialAnswerGenerator
from financial_ai.rag.dense_retriever import DenseRetriever
from financial_ai.rag.indexer import ChromaIndexer
from financial_ai.text2sql.generator import Text2SQLGenerator
from financial_ai.text2sql.executor import SQLExecutor
from financial_ai.db.repositories import execute_safe_select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["financial_assistant"])

# Initialize pipeline singletons
_query_router = QueryRouter()
_hybrid_executor = HybridExecutor()
_answer_generator = FinancialAnswerGenerator()
_dense_retriever = DenseRetriever()
_sql_generator = Text2SQLGenerator()
_sql_executor = SQLExecutor()
_chroma_indexer = ChromaIndexer()


@router.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    """End-to-end endpoint: Analyzes, routes (SQL/RAG/Hybrid), fuses, synthesizes, and verifies."""
    try:
        if req.override_route:
            analysis = _query_router.analyzer.analyze(req.query)
            decision = RouteDecision(
                route=req.override_route,
                analysis=analysis,
                rationale=f"Manually forced route: {req.override_route.value}",
            )
        else:
            decision = _query_router.route(req.query)

        evidence = _hybrid_executor.execute(decision)
        result = _answer_generator.generate(evidence)

        return QueryResponse(
            query=req.query,
            route=decision.route.value,
            answer=result["answer"],
            verification=result["verification"],
            evidence=result["evidence"],
        )
    except Exception as exc:
        logger.error("Query processing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sql", response_model=SQLDirectResponse)
def handle_sql(req: SQLDirectRequest):
    """Direct Text-to-SQL endpoint."""
    try:
        sql = _sql_generator.generate(req.query)
        exec_res = _sql_executor.execute(sql)
        return SQLDirectResponse(
            query=req.query,
            generated_sql=sql,
            success=exec_res["success"],
            rows=exec_res["rows"],
            markdown_table=exec_res["markdown_table"],
            error=exec_res.get("error"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/rag", response_model=RAGDirectResponse)
def handle_rag(req: RAGDirectRequest):
    """Direct RAG retrieval endpoint."""
    try:
        results = _dense_retriever.retrieve(
            query=req.query,
            ticker=req.ticker,
            section=req.section,
            top_k=req.top_k,
        )
        return RAGDirectResponse(
            query=req.query,
            results=results,
            total_found=len(results),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/companies")
def list_companies():
    """List supported companies and summaries from database."""
    try:
        companies = execute_safe_select("SELECT ticker, name, cik, sector, industry FROM companies ORDER BY ticker;")
        return {"companies": companies}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health", response_model=HealthResponse)
def health_check():
    """System health check."""
    db_ok = False
    try:
        execute_safe_select("SELECT 1;")
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database_connected=db_ok,
        chroma_indexed_chunks=_chroma_indexer.count(),
    )
