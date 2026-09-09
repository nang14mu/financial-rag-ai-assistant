"""Unit tests for metric_mapper module."""
import os
import pytest
from financial_ai.processing.metric_mapper import MetricMapper


def test_metric_mapper_loads_config():
    mapper = MetricMapper()
    all_metrics = mapper.get_all_metrics()
    assert "total_revenue" in all_metrics
    assert "net_income" in all_metrics
    assert "gross_profit" in all_metrics


def test_resolve_us_gaap_tag():
    mapper = MetricMapper()
    # Test mapping of revenue tags
    assert mapper.get_standard_metric("RevenueFromContractWithCustomerExcludingAssessedTax") == "total_revenue"
    assert mapper.get_standard_metric("NetIncomeLoss") == "net_income"
    assert mapper.get_standard_metric("GrossProfit") == "gross_profit"


def test_get_tags_for_metric():
    mapper = MetricMapper()
    tags = mapper.get_tags_for_metric("total_revenue")
    assert len(tags) >= 2
    assert "RevenueFromContractWithCustomerExcludingAssessedTax" in tags
