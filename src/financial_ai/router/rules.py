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

# Common abbreviations, typos, and financial slangs mapping
TICKER_ALIASES = {
    r"\b(nhà táo|táo khuyết|tao khuyet|nha tao|appl)\b": "AAPL",
    r"\b(yến vi|yen vi|đội xanh|doi xanh)\b": "NVDA",
    r"\b(tiểu phàm|tieu pham|vi nhuyễn|vi nhuyen)\b": "MSFT",
}

KEYWORD_ALIASES = {
    r"\b(dt|dthu|doang thu)\b": "doanh thu",
    r"\b(lnst|ln|loi nhuan)\b": "lợi nhuận",
    r"\b(bn|bao nhiu)\b": "bao nhiêu",
    r"\b(bctc)\b": "báo cáo tài chính",
    r"\b(tt|tang truong)\b": "tăng trưởng",
    r"\b(rui ro)\b": "rủi ro",
    r"\b(chien luoc)\b": "chiến lược",
    r"\b(giai thich|giai thik)\b": "giải thích",
    r"\b(nguyen nhan)\b": "nguyên nhân",
}


def normalize_query_text(query: str) -> str:
    """Normalize common abbreviations, typos, and slangs for financial analysis."""
    text = query.lower()
    for pattern, replacement in KEYWORD_ALIASES.items():
        text = re.sub(pattern, replacement, text)
    return text


def match_hybrid_patterns(query: str) -> bool:
    """Check if query matches compound quantitative + qualitative patterns."""
    q_norm = normalize_query_text(query)
    for w1, w2 in HYBRID_INDICATORS:
        if w1 in q_norm and w2 in q_norm:
            return True
    return False

