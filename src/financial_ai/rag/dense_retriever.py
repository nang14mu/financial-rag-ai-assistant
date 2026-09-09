"""Dense semantic vector retriever backed by ChromaDB with Parent-Document resolution."""
import logging
from typing import List, Dict, Any, Optional
from financial_ai.rag.indexer import ChromaIndexer
from financial_ai.rag.citations import format_citation

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Retrieves SEC 10-K chunks using semantic vector search and resolves Parent-Document full context."""

    def __init__(
        self,
        indexer: Optional[ChromaIndexer] = None,
        top_k: int = 5,
    ):
        self.indexer = indexer or ChromaIndexer()
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        ticker: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        section: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks matching query with dynamic metadata filters and Parent-Document resolution."""
        k = top_k or self.top_k

        # Build ChromaDB 'where' filter
        conditions = []
        if ticker:
            conditions.append({"ticker": {"$eq": ticker.upper()}})
        if fiscal_year:
            conditions.append({"fiscal_year": {"$eq": int(fiscal_year)}})
        if section:
            conditions.append({"section": {"$eq": section}})

        where_clause = None
        if len(conditions) == 1:
            where_clause = conditions[0]
        elif len(conditions) > 1:
            where_clause = {"$and": conditions}

        # Query more child candidates to account for parent deduplication
        candidate_k = min(k * 3, max(1, self.indexer.count()))
        logger.debug("Querying ChromaDB: query='%s', where=%s, candidate_k=%d", query, where_clause, candidate_k)

        try:
            results = self.indexer.collection.query(
                query_texts=[query],
                n_results=candidate_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaDB query error: %s. Retrying without filter...", exc)
            results = self.indexer.collection.query(
                query_texts=[query],
                n_results=candidate_k,
                include=["documents", "metadatas", "distances"],
            )

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)
        ids = results["ids"][0] if results["ids"] else [""] * len(docs)

        # Collect unique parent IDs
        parent_candidates: Dict[str, Dict[str, Any]] = {}
        for doc, meta, dist, cid in zip(docs, metas, distances, ids):
            similarity = round(max(0.0, 1.0 - float(dist)), 4)
            parent_id = meta.get("parent_id") or meta.get("chunk_id") or cid

            if parent_id not in parent_candidates or similarity > parent_candidates[parent_id]["similarity_score"]:
                parent_candidates[parent_id] = {
                    "matched_child_id": cid,
                    "matched_child_text": doc,
                    "child_meta": meta,
                    "similarity_score": similarity,
                }

        # Batch resolve parents from ParentDocStore
        all_parent_ids = list(parent_candidates.keys())
        parent_store_data = {}
        if hasattr(self.indexer, "parent_store") and self.indexer.parent_store:
            parent_store_data = self.indexer.parent_store.get_parents(all_parent_ids)

        retrieved_items: List[Dict[str, Any]] = []
        # Sort candidates by similarity score descending
        sorted_parent_ids = sorted(
            parent_candidates.keys(),
            key=lambda pid: parent_candidates[pid]["similarity_score"],
            reverse=True,
        )

        for pid in sorted_parent_ids[:k]:
            cand = parent_candidates[pid]
            sim = cand["similarity_score"]
            child_meta = cand["child_meta"]

            if pid in parent_store_data:
                parent_info = parent_store_data[pid]
                parent_text = parent_info["text"]
                parent_meta = parent_info["metadata"] or child_meta
            else:
                # Fallback to child text and metadata if parent not found in store
                parent_text = cand["matched_child_text"]
                parent_meta = child_meta

            citation = format_citation(parent_meta)
            retrieved_items.append({
                "chunk_id": pid,
                "text": parent_text,
                "metadata": parent_meta,
                "similarity_score": sim,
                "citation": citation,
                "matched_child_id": cand["matched_child_id"],
                "matched_child_text": cand["matched_child_text"],
            })

        logger.info("DenseRetriever resolved %d parent chunks for query '%s'", len(retrieved_items), query[:60])
        return retrieved_items
