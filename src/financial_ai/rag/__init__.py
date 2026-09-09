"""RAG package for financial document retrieval and indexing."""
from financial_ai.rag.citations import format_citation, parse_citation
from financial_ai.rag.indexer import ChromaIndexer
from financial_ai.rag.dense_retriever import DenseRetriever
from financial_ai.rag.bm25_retriever import BM25Retriever
from financial_ai.rag.hybrid_retriever import HybridRetriever
from financial_ai.rag.reranker import SimpleReranker

__all__ = [
    "format_citation",
    "parse_citation",
    "ChromaIndexer",
    "DenseRetriever",
    "BM25Retriever",
    "HybridRetriever",
    "SimpleReranker",
]
