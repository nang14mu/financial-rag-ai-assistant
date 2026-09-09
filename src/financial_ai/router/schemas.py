"""Pydantic schemas for intent analysis and query routing."""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RouteType(str, Enum):
    SQL_ONLY = "SQL_ONLY"
    RAG_ONLY = "RAG_ONLY"
    HYBRID = "HYBRID"


class QueryAnalysis(BaseModel):
    """Structured output extracted from the financial query."""
    query: str
    tickers: List[str] = Field(default_factory=list, description="Extracted company tickers (AAPL, MSFT, NVDA)")
    fiscal_years: List[int] = Field(default_factory=list, description="Target fiscal years (e.g. 2023, 2024, 2025)")
    target_sections: List[str] = Field(default_factory=list, description="Target 10-K sections (Item 1, Item 1A, Item 7)")
    primary_metrics: List[str] = Field(default_factory=list, description="Key metrics identified (revenue, net_income, margin, etc.)")
    is_quantitative: bool = Field(default=False, description="Whether query asks for exact numbers or financial calculations")
    is_qualitative: bool = Field(default=False, description="Whether query asks for strategies, explanations, risks")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RouteDecision(BaseModel):
    """Final routing decision with rationale."""
    route: RouteType
    analysis: QueryAnalysis
    rationale: str
