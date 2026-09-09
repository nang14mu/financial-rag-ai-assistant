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
