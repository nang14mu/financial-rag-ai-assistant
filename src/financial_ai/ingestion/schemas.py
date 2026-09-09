"""Pydantic schemas for SEC filings and XBRL ingestion."""
from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FilingMetadata(BaseModel):
    """Metadata of an SEC 10-K filing."""
    ticker: str
    cik: str
    accession_number: str
    form: str = "10-K"
    filing_date: date
    report_date: date
    fiscal_year: int
    primary_document: str
    document_url: str
    local_path: Optional[str] = None


class RawXBRLFactItem(BaseModel):
    """A single XBRL raw fact extracted from SEC Company Facts JSON."""
    ticker: str
    concept: str
    unit: str
    fiscal_year: int
    fiscal_period: str
    form: str
    filed_date: Optional[date]
    start_date: Optional[date]
    end_date: date
    value: float
    accession_number: str
