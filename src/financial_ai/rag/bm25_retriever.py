"""BM25 Lexical Retriever for matching exact financial terminology and product names."""
import re
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from financial_ai.rag.citations import format_citation

logger = logging.getLogger(__name__)


def simple_tokenize(text: str) -> List[str]:
    """Lowercase whitespace/punctuation tokenizer."""
    return re.findall(r"\w+", text.lower())


class BM25Retriever:
    """In-memory BM25 index over financial chunks."""

    def __init__(self, chunks: Optional[List[Dict[str, Any]]] = None):
        self.chunks = chunks or []
        self.bm25: Optional[BM25Okapi] = None
        if self.chunks:
            self.fit(self.chunks)

    def fit(self, chunks: List[Dict[str, Any]]):
        """Index the provided chunks into BM25."""
        self.chunks = chunks
        corpus = [simple_tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(corpus)
        logger.info("BM25Retriever indexed %d documents.", len(self.chunks))

    def retrieve(
        self,
        query: str,
        ticker: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve top_k chunks matching query keywords."""
        if not self.bm25 or not self.chunks:
            return []

        tokens = simple_tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)
        # Pair chunk with score
        scored_pairs = []
        for i, score in enumerate(scores):
            chunk = self.chunks[i]
            meta = chunk.get("metadata", {})

            # Filter by metadata if specified
            if ticker and meta.get("ticker", "").upper() != ticker.upper():
                continue
            if fiscal_year and int(meta.get("fiscal_year", 0)) != int(fiscal_year):
                continue

            scored_pairs.append((score, chunk))

        # Sort by score descending
        scored_pairs.sort(key=lambda x: x[0], reverse=True)
        top_pairs = scored_pairs[:top_k]

        results = []
        for score, ch in top_pairs:
            meta = ch.get("metadata", {})
            results.append({
                "chunk_id": ch.get("chunk_id"),
                "text": ch.get("text"),
                "metadata": meta,
                "bm25_score": round(float(score), 4),
                "citation": format_citation(meta),
            })
        return results
