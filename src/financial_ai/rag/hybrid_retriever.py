"""Hybrid Retriever combining Dense Vector and BM25 Lexical scores using Reciprocal Rank Fusion."""
import logging
from typing import List, Dict, Any, Optional
from financial_ai.rag.dense_retriever import DenseRetriever
from financial_ai.rag.bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines Dense Vector and BM25 search using Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: Optional[BM25Retriever] = None,
        rrf_k: int = 60,
    ):
        self.dense = dense_retriever
        self.bm25 = bm25_retriever
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        ticker: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        section: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid retrieval using RRF."""
        # 1. Dense retrieval
        dense_results = self.dense.retrieve(
            query=query,
            ticker=ticker,
            fiscal_year=fiscal_year,
            section=section,
            top_k=top_k * 2,
        )

        # If BM25 is not loaded, return dense results directly
        if not self.bm25 or not self.bm25.bm25:
            return dense_results[:top_k]

        # 2. BM25 retrieval
        bm25_results = self.bm25.retrieve(
            query=query,
            ticker=ticker,
            fiscal_year=fiscal_year,
            top_k=top_k * 2,
        )

        # 3. Reciprocal Rank Fusion
        rrf_scores: Dict[str, float] = {}
        item_map: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_results):
            cid = item.get("metadata", {}).get("parent_id") or item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            item_map[cid] = item

        for rank, item in enumerate(bm25_results):
            cid = item.get("metadata", {}).get("parent_id") or item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            if cid not in item_map:
                item_map[cid] = item

        # Sort by RRF score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda c: rrf_scores[c], reverse=True)

        final_results = []
        for cid in sorted_cids[:top_k]:
            item = dict(item_map[cid])
            item["hybrid_rrf_score"] = round(rrf_scores[cid], 5)
            final_results.append(item)

        logger.info("HybridRetriever fused %d items down to %d", len(sorted_cids), len(final_results))
        return final_results
