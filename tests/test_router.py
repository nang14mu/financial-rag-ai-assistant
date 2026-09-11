"""Unit tests for QueryRouter classification."""
import pytest
from financial_ai.router.router import QueryRouter
from financial_ai.router.schemas import RouteType


def test_router_pure_sql_queries():
    router = QueryRouter()

    queries = [
        "Doanh thu của Apple năm 2024 đạt bao nhiêu USD?",
        "So sánh Net Income của NVDA và MSFT qua 3 năm gần nhất",
        "Biên lợi nhuận gộp Gross Margin của NVIDIA năm 2024 là bao nhiêu?",
    ]

    for q in queries:
        decision = router.route(q)
        assert decision.route == RouteType.SQL_ONLY


def test_router_pure_rag_queries():
    router = QueryRouter()

    queries = [
        "Các yếu tố rủi ro chính về chuỗi cung ứng được Apple cảnh báo trong Item 1A là gì?",
        "Chiến lược phát triển sản phẩm AI và Copilot của Microsoft được nêu trong Item 1 như thế nào?",
        "NVIDIA mô tả sự cạnh tranh trong thị trường chip trung tâm dữ liệu ra sao?",
    ]

    for q in queries:
        decision = router.route(q)
        assert decision.route == RouteType.RAG_ONLY


def test_router_hybrid_queries():
    router = QueryRouter()

    queries = [
        "Doanh thu mảng Data Center của NVIDIA tăng trưởng bao nhiêu trong năm 2024 và ban lãnh đạo giải thích nguyên nhân do đâu trong MD&A?",
        "So sánh chi phí R&D của Apple và Microsoft trong năm 2023 và định hướng nghiên cứu phát triển được công bố trong 10-K",
    ]

    for q in queries:
        decision = router.route(q)
        assert decision.route == RouteType.HYBRID


def test_router_slang_and_abbreviations_tier1():
    """Test fast normalization for slangs and common abbreviations at Tier 1."""
    router = QueryRouter()

    # Typo + Slang: "nhà Táo" -> AAPL, "doang thu" -> doanh thu, "bn" -> bao nhiêu
    d1 = router.route("Doang thu của nhà Táo năm 2024 là bn usd?")
    assert d1.route == RouteType.SQL_ONLY
    assert "AAPL" in d1.analysis.tickers
    assert "total_revenue" in d1.analysis.primary_metrics

    # Abbreviation + Slang: "yến vi" -> NVDA, "lnst" -> lợi nhuận
    d2 = router.route("LNST của Yến Vi trong năm 2023")
    assert d2.route == RouteType.SQL_ONLY
    assert "NVDA" in d2.analysis.tickers
    assert "net_income" in d2.analysis.primary_metrics

    # Missing accents / typo: "appl", "muc 1a", "rui ro"
    d3 = router.route("Cac yeu to rui ro trong muc 1a cua appl")
    assert d3.route == RouteType.RAG_ONLY
    assert "AAPL" in d3.analysis.tickers
    assert "Item 1A" in d3.analysis.target_sections


def test_router_cascading_tier2_mock_llm():
    """Test cascading execution from Tier 1 to Tier 2 with mock LLM."""
    from unittest.mock import MagicMock
    from financial_ai.router.llm_classifier import LLMQueryClassifier

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"route": "SQL_ONLY", "tickers": ["AAPL"], "fiscal_years": [2024], "primary_metrics": ["total_revenue"], "rationale": "Resolved typo in user query"}'
    )

    classifier = LLMQueryClassifier(llm=mock_llm)
    # Query with no detectable ticker or low confidence triggers Tier 2
    router = QueryRouter(llm_classifier=classifier, confidence_threshold=0.85)

    decision = router.route("Bao nhiêu tiền bán được của quả táo năm 2024?")
    assert decision.route == RouteType.SQL_ONLY
    assert "AAPL" in decision.analysis.tickers
    assert "[Tier-2 LLM]" in decision.rationale
    assert mock_llm.invoke.called


def test_router_llm_failure_graceful_fallback():
    """Test graceful fallback to Tier 1 when Tier 2 LLM encounters an exception."""
    from unittest.mock import MagicMock
    from financial_ai.router.llm_classifier import LLMQueryClassifier

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("API connection timeout")

    classifier = LLMQueryClassifier(llm=mock_llm)
    router = QueryRouter(llm_classifier=classifier, confidence_threshold=0.99)

    # Even if LLM fails, router should not crash and should produce a valid fallback decision
    decision = router.route("Doanh thu của Apple năm 2024 đạt bao nhiêu USD?")
    assert decision.route == RouteType.SQL_ONLY
    assert "AAPL" in decision.analysis.tickers

