-- Drop existing views if exist
DROP VIEW IF EXISTS v_growth_and_margins;
DROP VIEW IF EXISTS v_annual_financial_summary;
DROP VIEW IF EXISTS v_segment_revenue;

-- 1. Semantic View: Annual Financial Summary
CREATE VIEW v_annual_financial_summary AS
SELECT
    ticker,
    fiscal_year,
    MAX(CASE WHEN metric_code = 'total_revenue' THEN value END) AS total_revenue,
    MAX(CASE WHEN metric_code = 'gross_profit' THEN value END) AS gross_profit,
    MAX(CASE WHEN metric_code = 'operating_income' THEN value END) AS operating_income,
    MAX(CASE WHEN metric_code = 'net_income' THEN value END) AS net_income,
    MAX(CASE WHEN metric_code = 'research_and_development' THEN value END) AS research_and_development,
    MAX(CASE WHEN metric_code = 'diluted_eps' THEN value END) AS diluted_eps,
    MAX(CASE WHEN metric_code = 'total_assets' THEN value END) AS total_assets,
    MAX(CASE WHEN metric_code = 'total_liabilities' THEN value END) AS total_liabilities,
    MAX(CASE WHEN metric_code = 'operating_cash_flow' THEN value END) AS operating_cash_flow
FROM financial_facts
WHERE fiscal_period = 'FY'
GROUP BY ticker, fiscal_year;

-- 2. Semantic View: Growth and Margins
CREATE VIEW v_growth_and_margins AS
SELECT
    ticker,
    fiscal_year,
    total_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (PARTITION BY ticker ORDER BY fiscal_year)) * 100.0
        / NULLIF(LAG(total_revenue) OVER (PARTITION BY ticker ORDER BY fiscal_year), 0),
        2
    ) AS revenue_growth_yoy_pct,
    ROUND((gross_profit * 100.0 / NULLIF(total_revenue, 0)), 2) AS gross_margin_pct,
    ROUND((operating_income * 100.0 / NULLIF(total_revenue, 0)), 2) AS operating_margin_pct,
    ROUND((net_income * 100.0 / NULLIF(total_revenue, 0)), 2) AS net_margin_pct
FROM v_annual_financial_summary;

-- 3. Semantic View: Segment and Product Dimension Revenue
CREATE VIEW v_segment_revenue AS
SELECT
    ticker,
    fiscal_year,
    dimension_type,
    dimension_name,
    value AS revenue,
    unit
FROM dimension_data
WHERE metric = 'revenue';
