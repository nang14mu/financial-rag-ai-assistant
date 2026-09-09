"""Schema provider supplying DDL and semantic view definitions to Text-to-SQL agents."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

SEMANTIC_VIEWS_DDL = """
-- 1. v_annual_financial_summary
-- Provides key annual P&L, balance sheet, and cash flow figures per company and fiscal year.
CREATE VIEW v_annual_financial_summary (
    ticker VARCHAR,                  -- 'AAPL', 'MSFT', 'NVDA'
    fiscal_year INT,                 -- e.g. 2023, 2024, 2025, 2026
    total_revenue NUMERIC,           -- Total revenue in USD
    gross_profit NUMERIC,            -- Gross profit in USD
    operating_income NUMERIC,        -- Operating profit/income in USD
    net_income NUMERIC,              -- Net income in USD
    research_and_development NUMERIC,-- R&D expenditure in USD
    diluted_eps NUMERIC,             -- Diluted earnings per share in USD/share
    total_assets NUMERIC,            -- Total assets in USD
    total_liabilities NUMERIC,       -- Total liabilities in USD
    operating_cash_flow NUMERIC      -- Cash flow from operations in USD
);

-- 2. v_growth_and_margins
-- Pre-calculates YoY revenue growth and profit margin percentages.
CREATE VIEW v_growth_and_margins (
    ticker VARCHAR,                  -- 'AAPL', 'MSFT', 'NVDA'
    fiscal_year INT,                 -- Fiscal year
    total_revenue NUMERIC,           -- Total revenue in USD
    revenue_growth_yoy_pct NUMERIC,  -- Percentage YoY growth in revenue (e.g. 15.67 = +15.67%)
    gross_margin_pct NUMERIC,        -- Gross profit margin % (gross_profit / revenue * 100)
    operating_margin_pct NUMERIC,    -- Operating margin % (operating_income / revenue * 100)
    net_margin_pct NUMERIC           -- Net profit margin % (net_income / revenue * 100)
);

-- 3. v_segment_revenue
-- Reports breakdown by product lines, market platforms, or geographic segments.
CREATE VIEW v_segment_revenue (
    ticker VARCHAR,                  -- 'AAPL', 'MSFT', 'NVDA'
    fiscal_year INT,                 -- Fiscal year
    dimension_type VARCHAR,          -- 'product_line', 'business_segment', 'market_platform', 'geographic'
    dimension_name VARCHAR,          -- e.g. 'Data Center', 'Gaming', 'iPhone', 'Services', 'Intelligent Cloud'
    revenue NUMERIC,                 -- Segment revenue in USD
    unit VARCHAR                     -- Currency unit ('USD')
);
"""

FEW_SHOT_EXAMPLES = [
    {
        "question": "Doanh thu và lợi nhuận ròng của Apple năm 2024 là bao nhiêu?",
        "sql": "SELECT fiscal_year, total_revenue, net_income FROM v_annual_financial_summary WHERE ticker = 'AAPL' AND fiscal_year = 2024;"
    },
    {
        "question": "So sánh Net Income của NVDA và MSFT qua 3 năm gần nhất",
        "sql": "SELECT ticker, fiscal_year, net_income FROM v_annual_financial_summary WHERE ticker IN ('NVDA', 'MSFT') ORDER BY fiscal_year DESC, ticker;"
    },
    {
        "question": "Biên lợi nhuận gộp Gross Margin của NVIDIA năm 2026 là bao nhiêu?",
        "sql": "SELECT fiscal_year, gross_margin_pct FROM v_growth_and_margins WHERE ticker = 'NVDA' AND fiscal_year = 2026;"
    },
    {
        "question": "Doanh thu mảng Data Center của NVIDIA qua các năm",
        "sql": "SELECT fiscal_year, dimension_name, revenue FROM v_segment_revenue WHERE ticker = 'NVDA' AND dimension_name = 'Data Center' ORDER BY fiscal_year DESC;"
    },
    {
        "question": "Tốc độ tăng trưởng doanh thu YoY của Microsoft năm gần nhất",
        "sql": "SELECT fiscal_year, total_revenue, revenue_growth_yoy_pct FROM v_growth_and_margins WHERE ticker = 'MSFT' ORDER BY fiscal_year DESC LIMIT 1;"
    }
]


class SchemaProvider:
    """Supplies context-rich database schema to Text-to-SQL models."""

    def get_ddl_context(self) -> str:
        return SEMANTIC_VIEWS_DDL.strip()

    def get_few_shot_context(self) -> List[Dict[str, str]]:
        return FEW_SHOT_EXAMPLES

    def get_full_prompt_context(self) -> str:
        examples_str = "\n\n".join([
            f"Question: {ex['question']}\nSQL: {ex['sql']}" for ex in FEW_SHOT_EXAMPLES
        ])
        return f"Database Views Schema:\n{self.get_ddl_context()}\n\nExamples:\n{examples_str}"
