"""Unit tests for SQLValidator security and syntax guardrails."""
import pytest
from financial_ai.text2sql.validator import SQLValidator


def test_valid_select_queries():
    validator = SQLValidator()

    query1 = "SELECT ticker, fiscal_year, total_revenue FROM v_annual_financial_summary WHERE ticker = 'AAPL';"
    is_valid, err = validator.validate(query1)
    assert is_valid is True
    assert err is None

    query2 = "SELECT fiscal_year, gross_margin_pct FROM v_growth_and_margins WHERE ticker = 'NVDA' ORDER BY fiscal_year DESC;"
    is_valid, err = validator.validate(query2)
    assert is_valid is True


def test_reject_destructive_queries():
    validator = SQLValidator()

    bad_queries = [
        "DROP TABLE companies;",
        "DELETE FROM financial_facts WHERE fiscal_year = 2024;",
        "UPDATE dimension_data SET value = 0;",
        "INSERT INTO companies (ticker) VALUES ('FAKE');",
        "TRUNCATE TABLE financial_facts;",
        "ALTER TABLE companies DROP COLUMN name;",
    ]

    for q in bad_queries:
        is_valid, err = validator.validate(q)
        assert is_valid is False, f"Expected query to be rejected: {q}"


def test_reject_unwhitelisted_tables():
    validator = SQLValidator()
    query = "SELECT * FROM secret_user_credentials;"
    is_valid, err = validator.validate(query)
    assert is_valid is False
    assert "secret_user_credentials" in err


def test_reject_multiple_statements():
    validator = SQLValidator()
    query = "SELECT * FROM v_annual_financial_summary; DROP TABLE companies;"
    is_valid, err = validator.validate(query)
    assert is_valid is False
