"""Reranker module to refine retrieval ordering."""
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SimpleReranker:
    """Lightweight cross-scoring reranker boosting exact financial query terms."""

    def __init__(self, keyword_weight: float = 0.35):
        self.keyword_weight = keyword_weight

    def rerank(self, query: str, items: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank items using combined semantic score and query term density."""
        if not items:
            return []

        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        if not query_terms:
            return items[:top_k]

        scored = []
        for it in items:
            base_score = it.get("similarity_score") or it.get("hybrid_rrf_score", 0.5)
            text_lower = it["text"].lower()

            matches = sum(1 for term in query_terms if term in text_lower)
            coverage = matches / len(query_terms)

            combined_score = (1 - self.keyword_weight) * base_score + (self.keyword_weight * coverage)
            item_copy = dict(it)
            item_copy["rerank_score"] = round(combined_score, 4)
            scored.append(item_copy)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]
