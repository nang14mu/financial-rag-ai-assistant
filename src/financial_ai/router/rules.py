"""Heuristic rules and keyword patterns for fast financial query classification."""
import re
from typing import List, Tuple
from financial_ai.router.schemas import RouteType

QUANT_KEYWORDS = [
    "doanh thu", "revenue", "sales", "net income", "lợi nhuận",
    "gross profit", "gross margin", "biên lợi nhuận", "biên gộp",
    "eps", "diluted eps", "cổ tức", "dividend",
    "total assets", "tổng tài sản", "nợ", "liabilities",
    "operating cash flow", "dòng tiền", "capex",
    "tăng trưởng", "growth", "tỷ lệ", "bao nhiêu", "how much", "how many",
    "so sánh số liệu", "compare revenue", "highest", "lowest",
]

QUAL_KEYWORDS = [
    "chiến lược", "strategy", "định hướng", "tầm nhìn",
    "rủi ro", "risk", "risk factors", "yếu tố rủi ro", "thách thức",
    "giải thích", "nguyên nhân", "lý do", "why", "explain", "because",
    "chuỗi cung ứng", "supply chain", "đối thủ", "competitor", "cạnh tranh",
    "pháp lý", "legal", "quy định", "regulation", "chính sách",
    "item 1", "item 1a", "mục 1", "mục 1a",
]

HYBRID_INDICATORS = [
    ("bao nhiêu", "nguyên nhân"),
    ("bao nhiêu", "tại sao"),
    ("bao nhiêu", "giải thích"),
    ("how much", "why"),
    ("how much", "explain"),
    ("tăng trưởng", "giải trình"),
    ("tăng trưởng", "nguyên nhân"),
    ("growth", "reasons"),
    ("growth", "md&a"),
    ("doanh thu", "chiến lược"),
    ("revenue", "strategy"),
    ("r&d", "định hướng"),
]


def match_hybrid_patterns(query: str) -> bool:
    """Check if query matches compound quantitative + qualitative patterns."""
    q_lower = query.lower()
    for w1, w2 in HYBRID_INDICATORS:
        if w1 in q_lower and w2 in q_lower:
            return True
    return False
