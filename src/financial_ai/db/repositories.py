"""Database repository functions for loading facts, querying views, and managing schema."""
import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from financial_ai.db.models import Company, FinancialFact, DimensionData
from financial_ai.db.session import get_db_session, get_engine

logger = logging.getLogger(__name__)


def apply_views(session: Optional[Session] = None):
    """Read views.sql and execute definitions to create/update semantic views."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    views_path = os.path.join(current_dir, "views.sql")
    if not os.path.exists(views_path):
        logger.warning("views.sql not found at %s", views_path)
        return

    with open(views_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split by semicolon to execute statement by statement
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    def _exec(s: Session):
        for stmt in statements:
            s.execute(text(stmt))
        logger.info("Successfully executed %d statements from views.sql", len(statements))

    if session:
        _exec(session)
    else:
        with get_db_session() as s:
            _exec(s)


def upsert_company(
    ticker: str,
    cik: str,
    name: str,
    sector: Optional[str],
    industry: Optional[str],
    fiscal_year_end_month: int,
    session: Optional[Session] = None,
) -> Company:
    """Insert or update company metadata."""
    def _do(s: Session):
        existing = s.query(Company).filter(Company.ticker == ticker.upper()).first()
        if existing:
            existing.cik = cik
            existing.name = name
            existing.sector = sector
            existing.industry = industry
            existing.fiscal_year_end_month = fiscal_year_end_month
            return existing
        company = Company(
            ticker=ticker.upper(),
            cik=cik,
            name=name,
            sector=sector,
            industry=industry,
            fiscal_year_end_month=fiscal_year_end_month,
        )
        s.add(company)
        return company

    if session:
        return _do(session)
    with get_db_session() as s:
        return _do(s)


def bulk_upsert_financial_facts(facts: List[Dict[str, Any]], session: Optional[Session] = None) -> int:
    """Insert or update financial facts with provenance."""
    if not facts:
        return 0

    def _do(s: Session) -> int:
        count = 0
        for f in facts:
            ticker = f["ticker"].upper()
            metric_code = f["metric_code"]
            fiscal_year = f["fiscal_year"]
            fiscal_period = f.get("fiscal_period", "FY")
            end_date = f["end_date"]

            existing = (
                s.query(FinancialFact)
                .filter(
                    FinancialFact.ticker == ticker,
                    FinancialFact.metric_code == metric_code,
                    FinancialFact.fiscal_year == fiscal_year,
                    FinancialFact.fiscal_period == fiscal_period,
                    FinancialFact.end_date == end_date,
                )
                .first()
            )
            if existing:
                existing.value = f["value"]
                existing.unit = f.get("unit", "USD")
                existing.concept = f["concept"]
                existing.accession_number = f.get("accession_number")
                existing.form = f.get("form", "10-K")
                existing.filed_date = f.get("filed_date")
            else:
                new_fact = FinancialFact(
                    ticker=ticker,
                    metric_code=metric_code,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    start_date=f.get("start_date"),
                    end_date=end_date,
                    value=f["value"],
                    unit=f.get("unit", "USD"),
                    concept=f["concept"],
                    accession_number=f.get("accession_number"),
                    form=f.get("form", "10-K"),
                    filed_date=f.get("filed_date"),
                    source=f.get("source", "SEC_COMPANY_FACTS"),
                )
                s.add(new_fact)
            count += 1
        return count

    if session:
        return _do(session)
    with get_db_session() as s:
        return _do(s)


def bulk_upsert_dimension_data(dim_records: List[Dict[str, Any]], session: Optional[Session] = None) -> int:
    """Insert or update generic dimension records."""
    if not dim_records:
        return 0

    def _do(s: Session) -> int:
        count = 0
        for d in dim_records:
            ticker = d["ticker"].upper()
            fy = d["fiscal_year"]
            dim_type = d["dimension_type"]
            dim_name = d["dimension_name"]
            metric = d.get("metric", "revenue")

            existing = (
                s.query(DimensionData)
                .filter(
                    DimensionData.ticker == ticker,
                    DimensionData.fiscal_year == fy,
                    DimensionData.dimension_type == dim_type,
                    DimensionData.dimension_name == dim_name,
                    DimensionData.metric == metric,
                )
                .first()
            )
            if existing:
                existing.value = d["value"]
                existing.unit = d.get("unit", "USD")
            else:
                new_dim = DimensionData(
                    ticker=ticker,
                    fiscal_year=fy,
                    dimension_type=dim_type,
                    dimension_name=dim_name,
                    metric=metric,
                    value=d["value"],
                    unit=d.get("unit", "USD"),
                )
                s.add(new_dim)
            count += 1
        return count

    if session:
        return _do(session)
    with get_db_session() as s:
        return _do(s)


def execute_safe_select(sql_query: str) -> List[Dict[str, Any]]:
    """Execute a read-only query and return records as dictionaries."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        keys = result.keys()
        rows = [dict(zip(keys, row)) for row in result.fetchall()]
        return rows
