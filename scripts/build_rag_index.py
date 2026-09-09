"""Script to clean 10-K filings, parse sections, apply Parent-Child hierarchical chunking, and build index."""
import os
import sys
import glob
import json
import logging
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath("src"))

from financial_ai.processing.html_cleaner import clean_sec_html
from financial_ai.processing.section_parser import SectionParser
from financial_ai.processing.chunker import SemanticFinancialChunker
from financial_ai.rag.indexer import ChromaIndexer
from financial_ai.rag.dense_retriever import DenseRetriever

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_index():
    raw_filings_dir = "./data/raw/filings"
    parser = SectionParser()
    chunker = SemanticFinancialChunker(
        subsection_threshold=1500,
        chunk_min_tokens=800,
        chunk_max_tokens=1500,
        child_chunk_tokens=180,
        child_overlap_tokens=35,
    )
    indexer = ChromaIndexer()

    # Reset collection and parent docstore to ensure clean build
    indexer.reset()

    all_parents: List[Dict[str, Any]] = []
    all_children: List[Dict[str, Any]] = []

    # Iterate over company filing directories
    tickers = [d for d in os.listdir(raw_filings_dir) if os.path.isdir(os.path.join(raw_filings_dir, d))]

    for ticker in tickers:
        ticker_dir = os.path.join(raw_filings_dir, ticker)
        html_files = glob.glob(os.path.join(ticker_dir, "*_10K.html"))

        for html_path in html_files:
            basename = os.path.basename(html_path)
            # Example: NVDA_2024_10K.html
            parts = basename.split("_")
            if len(parts) >= 2:
                fy = int(parts[1])
            else:
                fy = 2024

            logger.info("Processing filing %s (%s FY%d)...", basename, ticker, fy)
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

            logger.info("Cleaning HTML (%d chars)...", len(html_content))
            clean_text = clean_sec_html(html_content)
            logger.info("Cleaned text has %d chars. Extracting sections...", len(clean_text))

            sections = parser.extract_sections(
                clean_text=clean_text,
                ticker=ticker,
                fiscal_year=fy,
                save_to_disk=True,
            )

            filing_parents: List[Dict[str, Any]] = []
            filing_children: List[Dict[str, Any]] = []

            for sec_id, sec_data in sections.items():
                sec_name = sec_data["section_name"]
                subsections = sec_data["subsections"]

                hier = chunker.chunk_hierarchical(
                    ticker=ticker,
                    fiscal_year=fy,
                    section_id=sec_id,
                    section_name=sec_name,
                    subsections=subsections,
                )
                filing_parents.extend(hier["parents"])
                filing_children.extend(hier["children"])

            # Save hierarchical chunks for this filing only
            chunker.save_hierarchical_chunks(filing_parents, filing_children, ticker, fy)
            # Also save parents as primary legacy chunks file for compatibility
            chunker.save_chunks(filing_parents, ticker, fy, suffix="chunks")

            all_parents.extend(filing_parents)
            all_children.extend(filing_children)

    logger.info(
        "Total hierarchical chunks created: %d Parent Chunks (SQLite) | %d Child Chunks (ChromaDB)",
        len(all_parents),
        len(all_children),
    )

    # Index into ChromaDB & SQLite ParentDocStore
    logger.info("Indexing hierarchical chunks...")
    parent_count, child_count = indexer.index_hierarchical(
        parents=all_parents,
        children=all_children,
        batch_size=100,
    )
    logger.info(
        "Indexing complete! Total parents in SQLite: %d | Total child vectors in ChromaDB: %d",
        indexer.parent_store.count(),
        indexer.count(),
    )

    # Sanity Retrieval Verification
    retriever = DenseRetriever(indexer=indexer)
    sample_queries = [
        ("NVIDIA Data Center accelerated computing demand", "NVDA"),
        ("Apple supply chain and international trade risks", "AAPL"),
        ("Microsoft cloud infrastructure and Azure AI", "MSFT"),
    ]

    logger.info("--- RAG Small-to-Big Retrieval Sanity Check ---")
    for query, t in sample_queries:
        results = retriever.retrieve(query=query, ticker=t, top_k=2)
        logger.info("Query: '%s' (Ticker: %s) -> Returned %d resolved Parent chunks", query, t, len(results))
        for r in results:
            logger.info(
                "  * Citation: %s | Sim Score: %s | Chunk ID: %s (Matched Child: %s)",
                r["citation"],
                r["similarity_score"],
                r["chunk_id"],
                r.get("matched_child_id", ""),
            )
            preview = r["text"].replace("\n", " ")[:140]
            logger.info("    Parent Preview: %s...", preview)


if __name__ == "__main__":
    build_index()
