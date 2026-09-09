"""Request and Response Pydantic models for the FastAPI layer."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from financial_ai.router.schemas import RouteType


class QueryRequest(BaseModel):
    query: str = Field(..., example="Doanh thu mảng Data Center của NVIDIA tăng trưởng bao nhiêu trong năm 2026?")
    override_route: Optional[RouteType] = Field(None, description="Force routing path (SQL_ONLY, RAG_ONLY, HYBRID)")


class QueryResponse(BaseModel):
    query: str
    route: str
    answer: str
    verification: Dict[str, Any]
    evidence: Dict[str, Any]


class SQLDirectRequest(BaseModel):
    query: str = Field(..., example="Doanh thu của Apple qua 3 năm gần nhất")


class SQLDirectResponse(BaseModel):
    query: str
    generated_sql: str
    success: bool
    rows: List[Dict[str, Any]]
    markdown_table: str
    error: Optional[str] = None


class RAGDirectRequest(BaseModel):
    query: str = Field(..., example="Các rủi ro chuỗi cung ứng được Apple cảnh báo trong Item 1A")
    ticker: Optional[str] = None
    section: Optional[str] = None
    top_k: int = 4


class RAGDirectResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int


class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    chroma_indexed_chunks: int
