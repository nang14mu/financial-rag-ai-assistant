"""Script to normalize SEC XBRL facts, populate PostgreSQL, and create semantic views."""
import os
import sys
import yaml
import json
import logging
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.db.session import init_db, get_db_session
from financial_ai.db.repositories import (
    upsert_company,
    bulk_upsert_financial_facts,
    bulk_upsert_dimension_data,
    apply_views,
    execute_safe_select,
)
from financial_ai.ingestion.companyfacts_downloader import CompanyFactsDownloader
from financial_ai.processing.xbrl_normalizer import XBRLNormalizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Sample verified segment data extracted from 10-K MD&A disclosures across recent 3 years (in millions USD)
# Generic dimension schema: ticker, fiscal_year, dimension_type, dimension_name, metric, value, unit
SAMPLE_DIMENSIONS = [
    # NVIDIA (NVDA) Market Platforms (in USD, converted from 10-K reported figures)
    {"ticker": "NVDA", "fiscal_year": 2023, "dimension_type": "market_platform", "dimension_name": "Data Center", "metric": "revenue", "value": 15008000000.0, "unit": "USD"},
    {"ticker": "NVDA", "fiscal_year": 2024, "dimension_type": "market_platform", "dimension_name": "Data Center", "metric": "revenue", "value": 47525000000.0, "unit": "USD"},
    {"ticker": "NVDA", "fiscal_year": 2025, "dimension_type": "market_platform", "dimension_name": "Data Center", "metric": "revenue", "value": 115147000000.0, "unit": "USD"},

    {"ticker": "NVDA", "fiscal_year": 2023, "dimension_type": "market_platform", "dimension_name": "Gaming", "metric": "revenue", "value": 9067000000.0, "unit": "USD"},
    {"ticker": "NVDA", "fiscal_year": 2024, "dimension_type": "market_platform", "dimension_name": "Gaming", "metric": "revenue", "value": 10447000000.0, "unit": "USD"},
    {"ticker": "NVDA", "fiscal_year": 2025, "dimension_type": "market_platform", "dimension_name": "Gaming", "metric": "revenue", "value": 11300000000.0, "unit": "USD"},

    # Apple (AAPL) Product & Service Lines
    {"ticker": "AAPL", "fiscal_year": 2022, "dimension_type": "product_line", "dimension_name": "iPhone", "metric": "revenue", "value": 205489000000.0, "unit": "USD"},
    {"ticker": "AAPL", "fiscal_year": 2023, "dimension_type": "product_line", "dimension_name": "iPhone", "metric": "revenue", "value": 200583000000.0, "unit": "USD"},
    {"ticker": "AAPL", "fiscal_year": 2024, "dimension_type": "product_line", "dimension_name": "iPhone", "metric": "revenue", "value": 201183000000.0, "unit": "USD"},

    {"ticker": "AAPL", "fiscal_year": 2022, "dimension_type": "product_line", "dimension_name": "Services", "metric": "revenue", "value": 78129000000.0, "unit": "USD"},
    {"ticker": "AAPL", "fiscal_year": 2023, "dimension_type": "product_line", "dimension_name": "Services", "metric": "revenue", "value": 85200000000.0, "unit": "USD"},
    {"ticker": "AAPL", "fiscal_year": 2024, "dimension_type": "product_line", "dimension_name": "Services", "metric": "revenue", "value": 96169000000.0, "unit": "USD"},

    # Microsoft (MSFT) Business Segments
    {"ticker": "MSFT", "fiscal_year": 2022, "dimension_type": "business_segment", "dimension_name": "Intelligent Cloud", "metric": "revenue", "value": 75251000000.0, "unit": "USD"},
    {"ticker": "MSFT", "fiscal_year": 2023, "dimension_type": "business_segment", "dimension_name": "Intelligent Cloud", "metric": "revenue", "value": 87907000000.0, "unit": "USD"},
    {"ticker": "MSFT", "fiscal_year": 2024, "dimension_type": "business_segment", "dimension_name": "Intelligent Cloud", "metric": "revenue", "value": 105362000000.0, "unit": "USD"},

    {"ticker": "MSFT", "fiscal_year": 2022, "dimension_type": "business_segment", "dimension_name": "Productivity and Business Processes", "metric": "revenue", "value": 63364000000.0, "unit": "USD"},
    {"ticker": "MSFT", "fiscal_year": 2023, "dimension_type": "business_segment", "dimension_name": "Productivity and Business Processes", "metric": "revenue", "value": 69274000000.0, "unit": "USD"},
    {"ticker": "MSFT", "fiscal_year": 2024, "dimension_type": "business_segment", "dimension_name": "Productivity and Business Processes", "metric": "revenue", "value": 77349000000.0, "unit": "USD"},
]


def load_all():
    logger.info("Initializing database schema...")
    init_db()

    config_path = "./configs/companies.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        companies_cfg = yaml.safe_load(f).get("companies", {})

    downloader = CompanyFactsDownloader()
    normalizer = XBRLNormalizer()

    # Step 1: Upsert companies
    for ticker, info in companies_cfg.items():
        upsert_company(
            ticker=ticker,
            cik=info["cik"],
            name=info["name"],
            sector=info.get("sector"),
            industry=info.get("industry"),
            fiscal_year_end_month=info["fiscal_year_end_month"],
        )
    logger.info("Upserted %d companies into database.", len(companies_cfg))

    # Step 2: Normalize and load financial facts
    total_facts = 0
    for ticker, info in companies_cfg.items():
        cik = info["cik"]
        raw_json = downloader.load_company_facts(ticker=ticker, cik=cik)
        
        # Discover all available fiscal years for this company
        us_gaap = raw_json.get("facts", {}).get("us-gaap", {})
        fy_candidates = set()
        for concept_data in us_gaap.values():
            for entries in concept_data.get("units", {}).values():
                for item in entries:
                    if item.get("form") in ("10-K", "10-K/A") and item.get("fp") == "FY" and item.get("fy"):
                        fy_candidates.add(item["fy"])
        
        # Take the 3 most recent fiscal years
        sorted_years = sorted(list(fy_candidates), reverse=True)[:3]
        target_years = sorted(sorted_years)
        logger.info("Auto-detected 3 most recent fiscal years for %s: %s", ticker, target_years)

        facts = normalizer.normalize_company_facts(
            raw_facts_json=raw_json,
            ticker=ticker,
            target_fiscal_years=target_years,
        )
        normalizer.save_normalized_facts(facts, ticker)

        count = bulk_upsert_financial_facts(facts)
        total_facts += count
        logger.info("Loaded %d facts for %s", count, ticker)

    # Step 3: Load Dimension Data
    dim_count = bulk_upsert_dimension_data(SAMPLE_DIMENSIONS)
    logger.info("Loaded %d dimension records.", dim_count)

    # Step 4: Apply Semantic Views
    logger.info("Applying semantic views...")
    apply_views()

    # Step 5: Sanity Verification Query
    logger.info("--- Data Verification Sanity Check ---")
    summary_rows = execute_safe_select("SELECT * FROM v_annual_financial_summary ORDER BY ticker, fiscal_year DESC;")
    for r in summary_rows:
        logger.info(
            "[%s FY%s] Revenue: $%s | Net Income: $%s | EPS: $%s",
            r.get("ticker"),
            r.get("fiscal_year"),
            f"{float(r['total_revenue']):,.0f}" if r.get("total_revenue") else "N/A",
            f"{float(r['net_income']):,.0f}" if r.get("net_income") else "N/A",
            r.get("diluted_eps"),
        )

    margins_rows = execute_safe_select("SELECT * FROM v_growth_and_margins ORDER BY ticker, fiscal_year DESC;")
    for r in margins_rows:
        logger.info(
            "[%s FY%s] YoY Growth: %s%% | Gross Margin: %s%% | Net Margin: %s%%",
            r.get("ticker"),
            r.get("fiscal_year"),
            r.get("revenue_growth_yoy_pct"),
            r.get("gross_margin_pct"),
            r.get("net_margin_pct"),
        )


if __name__ == "__main__":
    load_all()
