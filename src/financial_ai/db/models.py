"""SQLAlchemy ORM models for structured financial data with full provenance."""
from datetime import date
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    ForeignKey,
    UniqueConstraint,
    Index,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Company(Base):
    """Company registry storing SEC CIK and filing schedule."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    cik = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    fiscal_year_end_month = Column(Integer, nullable=False)  # 9 for AAPL, 6 for MSFT, 1 for NVDA

    def __repr__(self) -> str:
        return f"<Company(ticker='{self.ticker}', name='{self.name}', cik='{self.cik}')>"


class FinancialFact(Base):
    """Normalized US-GAAP financial facts with complete SEC provenance."""
    __tablename__ = "financial_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    metric_code = Column(String(64), nullable=False, index=True)  # e.g., total_revenue, net_income
    fiscal_year = Column(Integer, nullable=False, index=True)     # e.g., 2023, 2024
    fiscal_period = Column(String(10), default="FY", nullable=False, index=True)  # FY, Q1, Q2, Q3, Q4
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(22, 4), nullable=False)
    unit = Column(String(20), default="USD", nullable=False)

    # Provenance tracking
    concept = Column(String(255), nullable=False)           # US-GAAP concept tag
    accession_number = Column(String(50), nullable=True)   # SEC filing accession number
    form = Column(String(10), default="10-K", nullable=False)
    filed_date = Column(Date, nullable=True)
    source = Column(String(100), default="SEC_COMPANY_FACTS", nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "metric_code",
            "fiscal_year",
            "fiscal_period",
            "end_date",
            name="uq_financial_fact_identity"
        ),
        Index("idx_fact_query", "ticker", "fiscal_year", "metric_code"),
    )

    def __repr__(self) -> str:
        return f"<FinancialFact({self.ticker}, {self.metric_code}, FY{self.fiscal_year}={self.value})>"


class DimensionData(Base):
    """Generic multi-dimensional financial segment and product line data."""
    __tablename__ = "dimension_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    dimension_type = Column(String(50), nullable=False, index=True)  # product_line, business_segment, geographic
    dimension_name = Column(String(100), nullable=False, index=True)  # Data Center, iPhone, Americas, etc.
    metric = Column(String(50), default="revenue", nullable=False)   # revenue, operating_income
    value = Column(Numeric(22, 4), nullable=False)
    unit = Column(String(20), default="USD", nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_year",
            "dimension_type",
            "dimension_name",
            "metric",
            name="uq_dimension_data_identity"
        ),
        Index("idx_dim_query", "ticker", "fiscal_year", "dimension_name"),
    )

    def __repr__(self) -> str:
        return f"<DimensionData({self.ticker}, FY{self.fiscal_year}, {self.dimension_name}={self.value})>"
